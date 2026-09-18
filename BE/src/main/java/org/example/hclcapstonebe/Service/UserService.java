package org.example.hclcapstonebe.Service;

import lombok.RequiredArgsConstructor;
import org.example.hclcapstonebe.DTO.Request.UpdateProfileRequest;
import org.example.hclcapstonebe.DTO.Response.UserProfileResponse;
import org.example.hclcapstonebe.Entities.User;
import org.example.hclcapstonebe.Exception.AppException;
import org.example.hclcapstonebe.Mapper.UserMapper;
import org.example.hclcapstonebe.Repository.UserRepository;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

    @Service
    @RequiredArgsConstructor
    public class UserService {

        private final UserRepository userRepository;
        private final SupabaseStorageService supabaseStorageService;
        private final UserMapper userMapper;                // ← injected

        private static final String IMAGE_BUCKET   = "images";
        private static final int    SIGNED_URL_TTL = 3600;

        public UserProfileResponse getProfile(String email) {
            User user = getUserByEmail(email);
            return toResponseWithSignedAvatar(user);
        }
        // ─── UPDATE MY PROFILE ────────────────────────────────────────────────────

        /**
         * Updates name, phoneNumber, and optionally avatar.
         * If a new avatar is uploaded:
         *   1. New avatar is validated and uploaded to Supabase images bucket
         *   2. The new storage path is saved to user.avatarImageUrl and persisted
         *   3. Only then is the OLD avatar deleted from Supabase images bucket
         *
         * @param email      current logged-in user's email (from JWT)
         * @param request    name + phoneNumber fields
         * @param avatarFile optional new avatar image (JPEG or PNG, max 10MB)
         */
        public UserProfileResponse updateProfile(String email,
                                                 UpdateProfileRequest request,
                                                 MultipartFile avatarFile) {
            User user = getUserByEmail(email);

            if (request.getName() != null && !request.getName().isBlank()) {
                user.setName(request.getName());
            }
            if (request.getPhoneNumber() != null && !request.getPhoneNumber().isBlank()) {
                user.setPhoneNumber(request.getPhoneNumber());
            }

            // Deferred until after userRepository.save() succeeds below --
            // real, confirmed bug: deleting the old avatar any earlier (even
            // just before save(), with no transaction tying the two
            // together) means a save failure after the delete reproduces
            // the exact same orphaned-avatar symptom -- the DB keeps
            // pointing at a path that's already gone from Supabase. Only
            // delete the old file once the new one is both uploaded AND
            // durably persisted as the user's real avatar.
            String oldAvatarPathToDelete = null;

            if (avatarFile != null && !avatarFile.isEmpty()) {
                // 1. Read + validate the NEW avatar FIRST. Real, confirmed bug:
                // this used to delete the OLD avatar before any of this ran,
                // so a rejected invalid-format upload returned a clean 400
                // (as if nothing happened) but permanently orphaned the
                // user's real, still-good avatar -- found live, only visible
                // by temporarily un-swallowing toResponseWithSignedAvatar's
                // own exception handler below. A validation/upload failure
                // must never destroy a still-good existing avatar.
                String originalName = avatarFile.getOriginalFilename() != null
                        ? avatarFile.getOriginalFilename()
                        : "avatar";
                // sanitizeFilename strips any directory components/traversal
                // sequences -- real, confirmed gap: the client-supplied
                // filename used to flow straight into the Supabase object
                // key unsanitized, so a crafted "../../documents/x.pdf"
                // filename could target a storage key outside the intended
                // images/<uuid>_... namespace.
                String storagePath = java.util.UUID.randomUUID() + "_" + sanitizeFilename(originalName);
                byte[] bytes;
                try {
                    bytes = avatarFile.getBytes();
                } catch (java.io.IOException e) {
                    throw new AppException("Failed to read file bytes: " + e.getMessage(),
                            HttpStatus.INTERNAL_SERVER_ERROR);
                }
                // Real MIME type from the file's own magic bytes, not the
                // client-supplied Content-Type header -- same bug #235 fixed
                // for document uploads (a non-browser client sending a generic
                // application/octet-stream otherwise gets a raw 500 leaked
                // from Supabase's own bucket MIME allowlist, confirmed live).
                // Also backfills the Swagger contract already promising a
                // clean 400 for an invalid avatar format, which nothing here
                // previously actually checked.
                String avatarContentType = detectImageContentType(bytes);

                // 2. Upload the NEW avatar.
                String newAvatarPath = supabaseStorageService.uploadFile(IMAGE_BUCKET, bytes, storagePath, avatarContentType);

                // 3. Remember the OLD avatar's path (before overwriting it
                // below), but don't delete it yet -- only after save().
                oldAvatarPathToDelete = user.getAvatarImageUrl();

                // 4. Save the new path.
                user.setAvatarImageUrl(newAvatarPath);
            }

            userRepository.save(user);

            // 5. Only now delete the OLD avatar -- the new one (if any) is
            // already confirmed valid, uploaded, AND durably persisted.
            if (oldAvatarPathToDelete != null && !oldAvatarPathToDelete.isBlank()) {
                supabaseStorageService.deleteFile(IMAGE_BUCKET, oldAvatarPathToDelete);
            }

            return toResponseWithSignedAvatar(user);
        }

        // ─── HELPERS ──────────────────────────────────────────────────────────────

        /**
         * MapStruct handles all scalar fields.
         * We manually attach the signed URL afterward since it's dynamic.
         */
        private UserProfileResponse toResponseWithSignedAvatar(User user) {
            UserProfileResponse response = userMapper.toResponse(user);   // MapStruct

            if (user.getAvatarImageUrl() != null && !user.getAvatarImageUrl().isBlank()) {
                try {
                    response.setAvatarSignedUrl(
                            supabaseStorageService.generateSignedUrl(
                                    IMAGE_BUCKET, user.getAvatarImageUrl(), SIGNED_URL_TTL
                            )
                    );
                } catch (Exception ignored) {
                    // Supabase unavailable or key misconfigured — serve profile without avatar
                }
            }

            return response;
        }

        private User getUserByEmail(String email) {
            return userRepository.findByEmailAndIsDeletedFalse(email)
                    .orElseThrow(() -> new AppException("User not found", HttpStatus.NOT_FOUND));
        }

        /**
         * Strips any directory components (so a "../../x" filename can't
         * escape the intended images/<uuid>_... storage key) and replaces
         * any remaining character outside a safe allowlist with "_". The
         * uuid prefix already guarantees uniqueness -- this exists purely
         * to keep the client-supplied name from influencing the storage
         * key's path structure at all.
         */
        private String sanitizeFilename(String filename) {
            String baseName;
            try {
                baseName = java.nio.file.Paths.get(filename).getFileName().toString();
            } catch (java.nio.file.InvalidPathException e) {
                // e.g. an embedded null byte -- Paths.get() itself rejects
                // it; fall back to a safe default rather than propagate.
                baseName = "avatar";
            }
            return baseName.replaceAll("[^A-Za-z0-9._-]", "_");
        }

        /**
         * Magic-byte format check -- same shape as DocumentService's, scoped
         * to the two formats this endpoint's own Swagger doc already promises
         * ("JPEG or PNG"). Real 400, not a raw Supabase-leaked 500, for
         * anything else (wrong file type, or a byte-for-byte match failure).
         */
        private String detectImageContentType(byte[] bytes) {
            if (bytes.length >= 4
                    && (bytes[0] & 0xFF) == 0x89 && bytes[1] == 0x50 && bytes[2] == 0x4E && bytes[3] == 0x47) {
                return "image/png";
            }
            if (bytes.length >= 3
                    && (bytes[0] & 0xFF) == 0xFF && (bytes[1] & 0xFF) == 0xD8 && (bytes[2] & 0xFF) == 0xFF) {
                return "image/jpeg";
            }
            throw new AppException("Invalid avatar format — only JPEG and PNG are supported", HttpStatus.BAD_REQUEST);
        }
    }