package org.example.hclcapstonebe.Service;

import org.example.hclcapstonebe.Exception.AppException;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.RestTemplate;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class SupabaseStorageServiceTest {

    @Mock
    private RestTemplate restTemplate;

    @InjectMocks
    private SupabaseStorageService supabaseStorageService;

    @Test
    void downloadFile_returnsBodyBytes_onSuccess() {
        ReflectionTestUtils.setField(supabaseStorageService, "supabaseUrl", "https://example.supabase.co");
        ReflectionTestUtils.setField(supabaseStorageService, "serviceRoleKey", "test-key");

        byte[] expectedBytes = "fake-file-content".getBytes();
        when(restTemplate.exchange(
                eq("https://example.supabase.co/storage/v1/object/documents/abc_test.jpg"),
                eq(HttpMethod.GET),
                any(HttpEntity.class),
                eq(byte[].class)
        )).thenReturn(new ResponseEntity<>(expectedBytes, HttpStatus.OK));

        byte[] result = supabaseStorageService.downloadFile("documents", "abc_test.jpg");

        assertArrayEquals(expectedBytes, result);
    }

    @Test
    void downloadFile_throwsAppException_onNetworkFailure() {
        ReflectionTestUtils.setField(supabaseStorageService, "supabaseUrl", "https://example.supabase.co");
        ReflectionTestUtils.setField(supabaseStorageService, "serviceRoleKey", "test-key");

        when(restTemplate.exchange(anyString(), eq(HttpMethod.GET), any(HttpEntity.class), eq(byte[].class)))
                .thenThrow(new RuntimeException("network error"));

        assertThrows(AppException.class, () ->
                supabaseStorageService.downloadFile("documents", "missing.jpg"));
    }
}
