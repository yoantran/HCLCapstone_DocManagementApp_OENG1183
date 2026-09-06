package org.example.hclcapstonebe.Service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.example.hclcapstonebe.Entities.Document;
import org.example.hclcapstonebe.Enums.RedactedPreviewStatus;
import org.example.hclcapstonebe.Repository.DocumentRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.RestTemplate;

import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class RedactedPreviewServiceTest {

    @Mock
    private DocumentRepository documentRepository;
    @Mock
    private SupabaseStorageService supabaseStorageService;
    @Mock
    private RestTemplate restTemplate;
    @Mock
    private SimpMessagingTemplate messagingTemplate;

    private RedactedPreviewService service;

    private Document sampleDocument(UUID id) {
        Document doc = new Document();
        doc.setId(id);
        doc.setName("test.docx");
        doc.setDocumentLink("some/path.docx");
        return doc;
    }

    @Test
    @SuppressWarnings("unchecked") // ArgumentCaptor.forClass(Map.class) is Mockito's own idiom for a generic type
    void generateAsyncMarksReadyAndNotifiesOnSuccess() throws Exception {
        service = new RedactedPreviewService(documentRepository, supabaseStorageService, restTemplate, messagingTemplate);
        ReflectionTestUtils.setField(service, "aiServiceUrl", "http://fake-ai");

        UUID docId = UUID.randomUUID();
        Document doc = sampleDocument(docId);
        when(documentRepository.findById(docId)).thenReturn(Optional.of(doc));
        when(supabaseStorageService.downloadFile(eq("documents"), eq("some/path.docx")))
                .thenReturn(new byte[]{1, 2, 3});
        byte[] fakePng = new byte[]{4, 5, 6};
        when(restTemplate.exchange(eq("http://fake-ai/apply-redaction"), eq(HttpMethod.POST), any(), eq(byte[].class)))
                .thenReturn(ResponseEntity.ok(fakePng));
        when(supabaseStorageService.uploadFile(eq("documents"), eq(fakePng), anyString(), eq("image/png")))
                .thenReturn("generated/path.png");

        JsonNode items = new ObjectMapper().readTree("[{\"page\":1}]");
        service.generateAsync(docId, "staff1@hcl.com", items);

        assertEquals(RedactedPreviewStatus.READY, doc.getRedactedPreviewStatus());
        assertEquals("generated/path.png", doc.getRedactedPreviewPath());
        verify(documentRepository).save(doc);

        ArgumentCaptor<Map<String, Object>> payloadCaptor = ArgumentCaptor.forClass(Map.class);
        verify(messagingTemplate).convertAndSendToUser(
                eq("staff1@hcl.com"), eq("/queue/redacted-preview-status"), payloadCaptor.capture());
        assertEquals("READY", payloadCaptor.getValue().get("status"));
    }

    @Test
    @SuppressWarnings("unchecked") // ArgumentCaptor.forClass(Map.class) is Mockito's own idiom for a generic type
    void generateAsyncMarksFailedAndNotifiesOnError() throws Exception {
        service = new RedactedPreviewService(documentRepository, supabaseStorageService, restTemplate, messagingTemplate);
        ReflectionTestUtils.setField(service, "aiServiceUrl", "http://fake-ai");

        UUID docId = UUID.randomUUID();
        Document doc = sampleDocument(docId);
        when(documentRepository.findById(docId)).thenReturn(Optional.of(doc));
        when(supabaseStorageService.downloadFile(anyString(), anyString()))
                .thenThrow(new RuntimeException("Supabase download failed"));

        JsonNode items = new ObjectMapper().readTree("[{\"page\":1}]");
        service.generateAsync(docId, "staff1@hcl.com", items);

        assertEquals(RedactedPreviewStatus.FAILED, doc.getRedactedPreviewStatus());
        assertEquals("Supabase download failed", doc.getRedactedPreviewFailureReason());
        verify(documentRepository).save(doc);

        ArgumentCaptor<Map<String, Object>> payloadCaptor = ArgumentCaptor.forClass(Map.class);
        verify(messagingTemplate).convertAndSendToUser(
                eq("staff1@hcl.com"), eq("/queue/redacted-preview-status"), payloadCaptor.capture());
        assertEquals("FAILED", payloadCaptor.getValue().get("status"));
    }
}
