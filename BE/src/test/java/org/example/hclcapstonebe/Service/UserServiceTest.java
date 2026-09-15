package org.example.hclcapstonebe.Service;

import org.example.hclcapstonebe.DTO.Request.UpdateProfileRequest;
import org.example.hclcapstonebe.DTO.Response.UserProfileResponse;
import org.example.hclcapstonebe.Entities.User;
import org.example.hclcapstonebe.Exception.AppException;
import org.example.hclcapstonebe.Mapper.UserMapper;
import org.example.hclcapstonebe.Repository.UserRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockMultipartFile;

import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class UserServiceTest {

    @Mock private UserRepository userRepository;
    @Mock private SupabaseStorageService supabaseStorageService;
    @Mock private UserMapper userMapper;

    @InjectMocks
    private UserService userService;

    private User buildUser(String existingAvatarPath) {
        User user = new User();
        user.setId(UUID.randomUUID());
        user.setEmail("staff1@hcl.com");
        user.setName("Staff1");
        user.setAvatarImageUrl(existingAvatarPath);
        return user;
    }

    // Real, confirmed bug: uploadAvatar deleted the user's existing
    // avatar from Supabase Storage BEFORE validating the new file's
    // format. A rejected invalid-format upload returned a clean 400 (as
    // if nothing happened) but permanently orphaned the real avatar --
    // reproduced live by uploading a real avatar, then an invalid-format
    // one, then finding the ORIGINAL avatar 404ing in Supabase on every
    // subsequent profile load, with zero logging anywhere pointing at
    // the real cause.
    @Test
    void updateProfile_rejectsInvalidAvatarFormat_withoutDeletingExistingAvatar() {
        User user = buildUser("existing-avatar-path.png");
        when(userRepository.findByEmailAndIsDeletedFalse("staff1@hcl.com")).thenReturn(Optional.of(user));

        MockMultipartFile invalidAvatar = new MockMultipartFile(
                "avatar", "fake.jpg", "image/jpeg", "not a real image".getBytes()
        );

        assertThrows(AppException.class, () ->
                userService.updateProfile("staff1@hcl.com", new UpdateProfileRequest(), invalidAvatar)
        );

        verify(supabaseStorageService, never()).deleteFile(any(), any());
        assertEquals("existing-avatar-path.png", user.getAvatarImageUrl());
    }

    @Test
    void updateProfile_validAvatar_deletesOldAvatarOnlyAfterNewOneUploads() {
        User user = buildUser("old-avatar-path.png");
        when(userRepository.findByEmailAndIsDeletedFalse("staff1@hcl.com")).thenReturn(Optional.of(user));
        when(supabaseStorageService.uploadFile(eq("images"), any(), any(), eq("image/png")))
                .thenReturn("new-avatar-path.png");
        when(userMapper.toResponse(user)).thenReturn(new UserProfileResponse());
        lenient().when(supabaseStorageService.generateSignedUrl(any(), any(), anyInt()))
                .thenReturn("https://signed.example/new-avatar-path.png");

        // Real PNG magic bytes -- detectImageContentType requires these to accept the file.
        byte[] pngBytes = {(byte) 0x89, 0x50, 0x4E, 0x47, 0, 0, 0, 0};
        MockMultipartFile validAvatar = new MockMultipartFile("avatar", "real.png", "image/png", pngBytes);

        userService.updateProfile("staff1@hcl.com", new UpdateProfileRequest(), validAvatar);

        verify(supabaseStorageService).deleteFile("images", "old-avatar-path.png");
        assertEquals("new-avatar-path.png", user.getAvatarImageUrl());
    }
}
