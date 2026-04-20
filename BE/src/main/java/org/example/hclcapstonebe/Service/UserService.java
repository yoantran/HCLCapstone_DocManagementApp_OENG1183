package org.example.hclcapstonebe.Service;


import org.example.hclcapstonebe.DTO.Request.UpdateProfileRequest;
import org.example.hclcapstonebe.DTO.Response.UserResponse;
import org.example.hclcapstonebe.Entities.User;
import org.example.hclcapstonebe.Exception.AppException;
import org.example.hclcapstonebe.Mapper.UserMapper;
import org.example.hclcapstonebe.Repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.util.UUID;

@Service
@RequiredArgsConstructor
public class UserService {

    private final UserRepository userRepository;
    private final UserMapper userMapper;                    // MapStruct

    public UserResponse getProfile(String email) {
        User user = getUserByEmail(email);
        return userMapper.toResponse(user);                 // MapStruct
    }

    public UserResponse updateProfile(String email,
                                      UpdateProfileRequest req,
                                      MultipartFile avatar) {
        User user = getUserByEmail(email);

        if (req != null) {
            if (req.getName() != null)        user.setName(req.getName());
            if (req.getPhoneNumber() != null) user.setPhoneNumber(req.getPhoneNumber());
        }

        if (avatar != null && !avatar.isEmpty()) {
            // TODO: replace with real S3 upload, store returned URL
            String avatarUrl = "avatars/" + UUID.randomUUID() + "_" + avatar.getOriginalFilename();
            user.setAvatarImageUrl(avatarUrl);
        }

        return userMapper.toResponse(userRepository.save(user)); // MapStruct
    }

    // ─── HELPER ───────────────────────────────────────────

    private User getUserByEmail(String email) {
        return userRepository.findByEmailAndIsDeletedFalse(email)
                .orElseThrow(() -> new AppException("User not found", HttpStatus.NOT_FOUND));
    }
}