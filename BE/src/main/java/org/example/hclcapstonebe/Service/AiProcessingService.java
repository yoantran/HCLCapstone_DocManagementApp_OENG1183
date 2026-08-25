package org.example.hclcapstonebe.Service;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.example.hclcapstonebe.Entities.Document;
import org.example.hclcapstonebe.Entities.Notification;
import org.example.hclcapstonebe.Entities.User;
import org.example.hclcapstonebe.Repository.DocumentRepository;
import org.example.hclcapstonebe.Repository.NotificationRepository;
import org.example.hclcapstonebe.Repository.UserRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * Fires the AI /process call after upload has already returned to the client.
 * Graceful degradation: the core upload flow doesn't depend on this
 * succeeding. Failure (AI service down/slow/timeout -- issue #222's own
 * marginal-timeout case included) is persisted visibly on the document
 * (aiProcessingFailed/aiFailureReason) and pushed to the uploader as a
 * notification, rather than leaving aiProcessed silently false forever with
 * no way to tell "still processing" apart from "permanently stuck."
 * Deliberately does NOT auto-retry -- AI's /process is fully synchronous,
 * one request at a time (#195); a blind retry would just queue a second
 * request against an already-overloaded service. Recovery today is a
 * manual re-upload; a safe automatic retry needs #195's concurrency
 * limit addressed first.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class AiProcessingService {

    private final RestTemplate restTemplate;
    private final DocumentRepository documentRepository;
    private final UserRepository userRepository;
    private final NotificationRepository notificationRepository;
    private final SimpMessagingTemplate messagingTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Value("${ai.service.url}")
    private String aiServiceUrl;

    @Async("aiTaskExecutor")
    public void processAsync(UUID documentId, byte[] fileBytes, String filename,
            BigDecimal proposedRepaymentAmount, String uploaderEmail) {
        try {
            Map<?, ?> result = callAiService(fileBytes, filename, proposedRepaymentAmount);
            if (result == null) {
                return;
            }

            Document doc = documentRepository.findById(documentId).orElse(null);
            if (doc == null) {
                return;
            }
            doc.setAiResult(objectMapper.writeValueAsString(result));
            doc.setAiProcessed(true);
            doc.setAiProcessingFailed(false);
            doc.setAiFailureReason(null);
            documentRepository.save(doc);

            notifyUploader(doc, uploaderEmail, "AI processing complete for " + doc.getName());
        } catch (Exception e) {
            log.warn("AI processing failed for document {}: {}", documentId, e.getMessage());
            markFailed(documentId, uploaderEmail, e.getMessage());
        }
    }

    private void markFailed(UUID documentId, String uploaderEmail, String reason) {
        Document doc = documentRepository.findById(documentId).orElse(null);
        if (doc == null) {
            return;
        }
        doc.setAiProcessingFailed(true);
        doc.setAiFailureReason(reason);
        documentRepository.save(doc);

        notifyUploader(doc, uploaderEmail, "AI processing failed for " + doc.getName() + " -- try re-uploading");
    }

    private Map<?, ?> callAiService(byte[] fileBytes, String filename, BigDecimal proposedRepaymentAmount) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("file", new ByteArrayResource(fileBytes) {
            @Override
            public String getFilename() {
                return filename;
            }
        });
        if (proposedRepaymentAmount != null) {
            body.add("proposed_monthly_repayment", proposedRepaymentAmount.toPlainString());
        }

        HttpEntity<MultiValueMap<String, Object>> request = new HttpEntity<>(body, headers);
        return restTemplate.postForObject(aiServiceUrl + "/process", request, Map.class);
    }

    private void notifyUploader(Document doc, String uploaderEmail, String content) {
        User uploader = userRepository.findByEmailAndIsDeletedFalse(uploaderEmail).orElse(null);
        if (uploader == null) {
            return;
        }

        Notification notification = Notification.builder()
                .triggeredDocument(doc)
                .content(content)
                .receiver(uploader)
                .build();
        notificationRepository.save(notification);

        Map<String, Object> wsPayload = new HashMap<>();
        wsPayload.put("id", notification.getId());
        wsPayload.put("content", content);
        wsPayload.put("documentId", doc.getId());
        wsPayload.put("documentName", doc.getName());
        wsPayload.put("hasRead", false);
        wsPayload.put("createdAt", LocalDateTime.now().toString());

        messagingTemplate.convertAndSendToUser(uploaderEmail, "/queue/notifications", wsPayload);
    }
}
