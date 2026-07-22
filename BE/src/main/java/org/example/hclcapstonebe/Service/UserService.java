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
                String newAvatarPath = supabaseStorageService.uploadFile(IMAGE_BUCKET, bytes, storagePath, avatarFile.getContentType());
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
    }