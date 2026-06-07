package org.example.hclcapstonebe.Service;

import lombok.RequiredArgsConstructor;
import org.example.hclcapstonebe.Exception.AppException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.Map;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class SupabaseStorageService {

    @Value("${supabase.url}")
    private String supabaseUrl;

    @Value("${supabase.service-role-key}")
    private String serviceRoleKey;

    private final RestTemplate restTemplate;

    // ─── UPLOAD ───────────────────────────────────────────────────────────────

    /**
     * Uploads a file to the given Supabase bucket.
     *
     * @param bucket   "documents" or "images"
     * @param file     the multipart file from the request
     * @return         the storage path inside the bucket  (e.g. "abc123_report.pdf")
     *                 Store this path in DB; use it later to generate signed URLs.
     */
    public String uploadFile(String bucket, MultipartFile file) {
        String originalName = file.getOriginalFilename() != null
                ? file.getOriginalFilename()
                : "unnamed";

        // Unique path so files never collide
        String storagePath = UUID.randomUUID() + "_" + originalName;

        String uploadUrl = supabaseUrl
                + "/storage/v1/object/"
                + bucket + "/"
                + storagePath;

        HttpHeaders headers = new HttpHeaders();
        headers.set("Authorization", "Bearer " + serviceRoleKey);
        headers.setContentType(MediaType.parseMediaType(
                file.getContentType() != null ? file.getContentType() : "application/octet-stream"
        ));

        byte[] bytes;
        try {
            bytes = file.getBytes();
        } catch (IOException e) {
            throw new AppException("Failed to read file bytes: " + e.getMessage(),
                    HttpStatus.INTERNAL_SERVER_ERROR);
        }

        HttpEntity<byte[]> entity = new HttpEntity<>(bytes, headers);

        try {
            ResponseEntity<String> response = restTemplate.exchange(
                    uploadUrl, HttpMethod.POST, entity, String.class
            );
            if (!response.getStatusCode().is2xxSuccessful()) {
                throw new AppException("Supabase upload failed: " + response.getBody(),
                        HttpStatus.INTERNAL_SERVER_ERROR);
            }
        } catch (Exception e) {
            throw new AppException("Supabase upload error: " + e.getMessage(),
                    HttpStatus.INTERNAL_SERVER_ERROR);
        }

        return storagePath;   // persist this in Document.signedUrl / Image.imageLink
    }

    // ─── SIGNED URL ───────────────────────────────────────────────────────────

    /**
     * Generates a temporary signed URL for private bucket access.
     * The FE uses this URL directly to render/download the file.
     *
     * @param bucket       "documents" or "images"
     * @param storagePath  the path returned by uploadFile()
     * @param expiresIn    seconds until the URL expires (e.g. 3600 = 1 hour)
     * @return             a signed URL string
     */
    public String generateSignedUrl(String bucket, String storagePath, int expiresIn) {
        String signUrl = supabaseUrl
                + "/storage/v1/object/sign/"
                + bucket + "/"
                + storagePath;

        HttpHeaders headers = new HttpHeaders();
        headers.set("Authorization", "Bearer " + serviceRoleKey);
        headers.setContentType(MediaType.APPLICATION_JSON);

        Map<String, Object> body = Map.of("expiresIn", expiresIn);
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);

        try {
            ResponseEntity<Map> response = restTemplate.exchange(
                    signUrl, HttpMethod.POST, entity, Map.class
            );
            if (response.getBody() == null || !response.getBody().containsKey("signedURL")) {
                throw new AppException("Supabase did not return a signed URL",
                        HttpStatus.INTERNAL_SERVER_ERROR);
            }
            // Supabase returns a relative path; prepend the project URL
//            String signedPath = (String) response.getBody().get("signedURL");
//            return supabaseUrl + signedPath;
            String signedPath = (String) response.getBody().get("signedURL");

// Remove any leading slash from signedPath to avoid double slash
            if (signedPath.startsWith("/")) {
                signedPath = signedPath.substring(1);
            }

            return supabaseUrl + "/storage/v1/" + signedPath;
        } catch (Exception e) {
            throw new AppException("Failed to generate signed URL: " + e.getMessage(),
                    HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    // ─── DELETE ───────────────────────────────────────────────────────────────

    /**
     * Deletes a file from the Supabase bucket.
     * Call this only if you decide to hard-delete; skip for soft-delete flows.
     *
     * @param bucket       "documents" or "images"
     * @param storagePath  the path returned by uploadFile()
     */
    public void deleteFile(String bucket, String storagePath) {
        String deleteUrl = supabaseUrl
                + "/storage/v1/object/"
                + bucket + "/"
                + storagePath;

        HttpHeaders headers = new HttpHeaders();
        headers.set("Authorization", "Bearer " + serviceRoleKey);

        HttpEntity<Void> entity = new HttpEntity<>(headers);

        try {
            restTemplate.exchange(deleteUrl, HttpMethod.DELETE, entity, String.class);
        } catch (Exception e) {
            // Log but don't crash — DB soft-delete already happened
            System.err.println("Supabase delete warning: " + e.getMessage());
        }
    }
}
