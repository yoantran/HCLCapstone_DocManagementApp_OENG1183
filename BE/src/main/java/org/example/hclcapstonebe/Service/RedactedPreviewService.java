package org.example.hclcapstonebe.Service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.example.hclcapstonebe.Entities.Document;
import org.example.hclcapstonebe.Enums.RedactedPreviewStatus;
import org.example.hclcapstonebe.Exception.AppException;
import org.example.hclcapstonebe.Repository.DocumentRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.*;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * Generates the redacted preview image in the background so no HTTP request
 * thread blocks on Modal's /apply-redaction call, whose latency isn't
 * reliably bounded (live samples: 240s, >302s -- see issues #337/#338).
 * Mirrors AiProcessingService's async + notify pattern for /process.
 * Deliberately never auto-retries on its own -- same policy as
 * AiProcessingService (see its class comment): a FAILED status only moves
 * again when DocumentService.getRedactedPreviewStatus is called with
 * retry=true (an explicit user action), never automatically.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class RedactedPreviewService {

    private static final String BUCKET = "documents";

    private final DocumentRepository documentRepository;
    private final SupabaseStorageService supabaseStorageService;
    private final RestTemplate restTemplate;
    private final SimpMessagingTemplate messagingTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Value("${ai.service.url}")
    private String aiServiceUrl;

    @Async("aiTaskExecutor")
    public void generateAsync(UUID documentId, String requesterEmail, JsonNode redactionItems) {
        Document doc = documentRepository.findById(documentId).orElse(null);
        if (doc == null) {
            return;
        }
        try {
            byte[] originalBytes = supabaseStorageService.downloadFile(BUCKET, doc.getDocumentLink());
            byte[] pngBytes = callApplyRedaction(originalBytes, doc.getName(), redactionItems);

            String storagePath = UUID.randomUUID() + "_redacted_preview.png";
            String uploadedPath = supabaseStorageService.uploadFile(BUCKET, pngBytes, storagePath, "image/png");

            doc.setRedactedPreviewStatus(RedactedPreviewStatus.READY);
            doc.setRedactedPreviewPath(uploadedPath);
            doc.setRedactedPreviewFailureReason(null);
            documentRepository.save(doc);

            notifyRequester(requesterEmail, documentId, RedactedPreviewStatus.READY, null);
        } catch (Exception e) {
            log.warn("Redacted preview generation failed for document {}: {}", documentId, e.getMessage());
            doc.setRedactedPreviewStatus(RedactedPreviewStatus.FAILED);
            doc.setRedactedPreviewFailureReason(e.getMessage());
            documentRepository.save(doc);

            notifyRequester(requesterEmail, documentId, RedactedPreviewStatus.FAILED, e.getMessage());
        }
    }

    private byte[] callApplyRedaction(byte[] fileBytes, String filename, JsonNode redactionItems) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("file", new ByteArrayResource(fileBytes) {
            @Override
            public String getFilename() {
                return filename;
            }
        });
        try {
            body.add("items", objectMapper.writeValueAsString(redactionItems));
        } catch (JsonProcessingException e) {
            throw new AppException("Failed to serialize redaction items", HttpStatus.INTERNAL_SERVER_ERROR);
        }

        HttpEntity<MultiValueMap<String, Object>> request = new HttpEntity<>(body, headers);
        ResponseEntity<byte[]> response = restTemplate.exchange(
                aiServiceUrl + "/apply-redaction", HttpMethod.POST, request, byte[].class
        );
        if (!response.getStatusCode().is2xxSuccessful() || response.getBody() == null) {
            throw new AppException("AI apply-redaction failed: " + response.getStatusCode(),
                    HttpStatus.INTERNAL_SERVER_ERROR);
        }
        return response.getBody();
    }

    private void notifyRequester(String requesterEmail, UUID documentId, RedactedPreviewStatus status, String failureReason) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("documentId", documentId.toString());
        payload.put("status", status.name());
        payload.put("failureReason", failureReason);
        messagingTemplate.convertAndSendToUser(requesterEmail, "/queue/redacted-preview-status", payload);
    }
}
