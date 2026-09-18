package org.example.hclcapstonebe.Service;

import org.example.hclcapstonebe.DTO.Request.UpdateProfileRequest;
import org.example.hclcapstonebe.DTO.Response.UserProfileResponse;
import org.example.hclcapstonebe.Entities.User;
import org.example.hclcapstonebe.Exception.AppException;
import org.example.hclcapstonebe.Mapper.UserMapper;
import org.example.hclcapstonebe.Repository.UserRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockMultipartFile;

import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
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

    // Real finding from reviewing #356's own fix: the old avatar was
    // deleted from Supabase BEFORE userRepository.save(user) ran, with no
    // transaction tying the two together. A save failure after the
    // delete reproduces #355's exact symptom one step later -- the DB
    // keeps pointing at the just-deleted old path. Deleting the old file
    // only after save() succeeds means a save failure never touches the
    // old (still-good) avatar.
    @Test
    void updateProfile_doesNotDeleteOldAvatarWhenDatabaseSaveFails() {
        User user = buildUser("old-avatar-path.png");
        when(userRepository.findByEmailAndIsDeletedFalse("staff1@hcl.com")).thenReturn(Optional.of(user));
        when(supabaseStorageService.uploadFile(eq("images"), any(), any(), eq("image/png")))
                .thenReturn("new-avatar-path.png");
        when(userRepository.save(any())).thenThrow(new RuntimeException("DB blip"));

        byte[] pngBytes = {(byte) 0x89, 0x50, 0x4E, 0x47, 0, 0, 0, 0};
        MockMultipartFile validAvatar = new MockMultipartFile("avatar", "real.png", "image/png", pngBytes);

        assertThrows(RuntimeException.class, () ->
                userService.updateProfile("staff1@hcl.com", new UpdateProfileRequest(), validAvatar)
        );

        verify(supabaseStorageService, never()).deleteFile(any(), any());
    }

    // Real finding: storagePath was built directly from the client-
    // supplied avatarFile.getOriginalFilename() with no sanitization, so
    // a crafted filename with ".." segments flows straight into the
    // Supabase object key -- risking a key outside the intended
    // images/<uuid>_... namespace, since the service-role key has broad
    // bucket access.
    @Test
    void updateProfile_sanitizesPathTraversalInAvatarFilename() {
        User user = buildUser(null);
        when(userRepository.findByEmailAndIsDeletedFalse("staff1@hcl.com")).thenReturn(Optional.of(user));
        when(supabaseStorageService.uploadFile(eq("images"), any(), any(), eq("image/png")))
                .thenReturn("stored-path.png");

        byte[] pngBytes = {(byte) 0x89, 0x50, 0x4E, 0x47, 0, 0, 0, 0};
        MockMultipartFile maliciousAvatar = new MockMultipartFile(
                "avatar", "../../documents/some-other-storage-path.pdf", "image/png", pngBytes
        );

        userService.updateProfile("staff1@hcl.com", new UpdateProfileRequest(), maliciousAvatar);

        ArgumentCaptor<String> storagePathCaptor = ArgumentCaptor.forClass(String.class);
        verify(supabaseStorageService).uploadFile(eq("images"), any(), storagePathCaptor.capture(), eq("image/png"));
        String storagePath = storagePathCaptor.getValue();
        assertFalse(storagePath.contains("/"), "storage path must not contain a path separator: " + storagePath);
        assertFalse(storagePath.contains(".."), "storage path must not contain a traversal sequence: " + storagePath);
    }
}
