package org.example.hclcapstonebe.Service;

import lombok.RequiredArgsConstructor;
import org.example.hclcapstonebe.Exception.AppException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.HashMap;
import java.util.List;
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
     * @param bucket      "documents" or "images"
     * @param bytes       the file content bytes
     * @param storagePath the storage path inside the bucket (e.g. "abc123_report.pdf")
     * @param contentType the MIME content type of the file
     * @return            the storage path inside the bucket (e.g. "abc123_report.pdf")
     *                    Store this path in DB; use it later to generate signed URLs.
     */
    public String uploadFile(String bucket, byte[] bytes, String storagePath, String contentType) {
        String uploadUrl = supabaseUrl
                + "/storage/v1/object/"
                + bucket + "/"
                + storagePath;

        HttpHeaders headers = new HttpHeaders();
        headers.set("Authorization", "Bearer " + serviceRoleKey);
        headers.setContentType(MediaType.parseMediaType(contentType));

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

    /**
     * Batch version of generateSignedUrl -- one real Supabase call for every
     * path instead of one call per path (issue #260). Supabase Storage's own
     * batch-sign endpoint (POST .../object/sign/{bucket}, body {paths, expiresIn})
     * returns every signed URL in a single request; verified live against the
     * real project before wiring this in, not assumed from docs.
     *
     * @param bucket       "documents" or "images"
     * @param storagePaths the paths returned by uploadFile() -- duplicates and
     *                     empty input are both handled (Supabase itself
     *                     dedupes; an empty list short-circuits with no call)
     * @return             storagePath -> signed URL. A path Supabase reports
     *                     an error for is simply omitted, not thrown -- callers
     *                     already treat a missing signed URL as "not
     *                     accessible", the same fail-closed behavior
     *                     generateSignedUrl's own exception path leads to for
     *                     a single lookup.
     */
    public Map<String, String> generateSignedUrls(String bucket, List<String> storagePaths, int expiresIn) {
        if (storagePaths == null || storagePaths.isEmpty()) {
            return Map.of();
        }

        String signUrl = supabaseUrl + "/storage/v1/object/sign/" + bucket;

        HttpHeaders headers = new HttpHeaders();
        headers.set("Authorization", "Bearer " + serviceRoleKey);
        headers.setContentType(MediaType.APPLICATION_JSON);

        Map<String, Object> body = Map.of("expiresIn", expiresIn, "paths", storagePaths);
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);

        try {
            ResponseEntity<List> response = restTemplate.exchange(
                    signUrl, HttpMethod.POST, entity, List.class
            );
            List<Map<String, Object>> results = response.getBody();
            if (results == null) {
                throw new AppException("Supabase did not return signed URLs", HttpStatus.INTERNAL_SERVER_ERROR);
            }

            Map<String, String> signedUrls = new HashMap<>();
            for (Map<String, Object> result : results) {
                Object path = result.get("path");
                Object signedURL = result.get("signedURL");
                if (path == null || signedURL == null) {
                    continue; // Supabase reported an error for this one path -- omit, don't fail the whole batch
                }
                String signedPath = (String) signedURL;
                if (signedPath.startsWith("/")) {
                    signedPath = signedPath.substring(1);
                }
                signedUrls.put((String) path, supabaseUrl + "/storage/v1/" + signedPath);
            }
            return signedUrls;
        } catch (Exception e) {
            throw new AppException("Failed to generate signed URLs: " + e.getMessage(),
                    HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    // ─── DOWNLOAD ─────────────────────────────────────────────────────────────

    /**
     * Downloads raw file bytes from the given Supabase bucket.
     *
     * @param bucket       "documents" or "images"
     * @param storagePath  the path returned by uploadFile()
     * @return             the raw file bytes
     */
    public byte[] downloadFile(String bucket, String storagePath) {
        String downloadUrl = supabaseUrl
                + "/storage/v1/object/"
                + bucket + "/"
                + storagePath;

        HttpHeaders headers = new HttpHeaders();
        headers.set("Authorization", "Bearer " + serviceRoleKey);
        HttpEntity<Void> entity = new HttpEntity<>(headers);

        try {
            ResponseEntity<byte[]> response = restTemplate.exchange(
                    downloadUrl, HttpMethod.GET, entity, byte[].class
            );
            if (!response.getStatusCode().is2xxSuccessful() || response.getBody() == null) {
                throw new AppException("Supabase download failed: " + response.getStatusCode(),
                        HttpStatus.INTERNAL_SERVER_ERROR);
            }
            return response.getBody();
        } catch (AppException e) {
            throw e;
        } catch (Exception e) {
            throw new AppException("Supabase download error: " + e.getMessage(),
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
