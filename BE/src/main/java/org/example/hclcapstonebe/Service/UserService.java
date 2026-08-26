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
         *   1. Old avatar is deleted from Supabase images bucket
         *   2. New avatar is uploaded to Supabase images bucket
         *   3. The New storage path is saved to user.avatarImageUrl
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

            if (avatarFile != null && !avatarFile.isEmpty()) {
                // 1. Delete old avatar from Supabase
                if (user.getAvatarImageUrl() != null && !user.getAvatarImageUrl().isBlank()) {
                    supabaseStorageService.deleteFile(IMAGE_BUCKET, user.getAvatarImageUrl());
                }
                // 2. Upload new avatar
                String originalName = avatarFile.getOriginalFilename() != null
                        ? avatarFile.getOriginalFilename()
                        : "avatar";
                String storagePath = java.util.UUID.randomUUID() + "_" + originalName;
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
                String newAvatarPath = supabaseStorageService.uploadFile(IMAGE_BUCKET, bytes, storagePath, avatarContentType);
                // 3. Save path
                user.setAvatarImageUrl(newAvatarPath);
            }

            userRepository.save(user);
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