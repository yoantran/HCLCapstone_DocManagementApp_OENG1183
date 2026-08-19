package org.example.hclcapstonebe.Service;

import org.example.hclcapstonebe.DTO.Response.DocumentResponse;
import org.example.hclcapstonebe.Entities.Department;
import org.example.hclcapstonebe.Entities.Document;
import org.example.hclcapstonebe.Entities.User;
import org.example.hclcapstonebe.Enums.ScanStatus;
import org.example.hclcapstonebe.Mapper.DocumentMapper;
import org.example.hclcapstonebe.Repository.DocumentRepository;
import org.example.hclcapstonebe.Repository.NotificationRepository;
import org.example.hclcapstonebe.Repository.UserRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.web.client.RestTemplate;

import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class DocumentServiceTest {

    @Mock private DocumentRepository documentRepository;
    @Mock private UserRepository userRepository;
    @Mock private NotificationRepository notificationRepository;
    @Mock private SimpMessagingTemplate messagingTemplate;
    @Mock private DocumentMapper documentMapper;
    @Mock private SupabaseStorageService supabaseStorageService;
    @Mock private ClamAvScannerService clamAvScannerService;
    @Mock private AiProcessingService aiProcessingService;
    @Mock private RestTemplate restTemplate;

    @InjectMocks
    private DocumentService documentService;

    private static final String AI_RESULT_JSON = """
            {"fields":{"applicant_name":"Jo Worker","bsb":"123-456","salary":5000},
             "sensitive_field_keys":["applicant_name","bsb"],
             "redaction":{"type":"boxes","items":[]}}
            """;

    private Document buildDoc(UUID uploaderId, UUID departmentId, String aiResult) {
        User uploader = new User();
        uploader.setId(uploaderId);
        Department dept = new Department();
        dept.setId(departmentId);
        return Document.builder()
                .id(UUID.randomUUID())
                .uploader(uploader)
                .department(dept)
                .scanStatus(ScanStatus.CLEAN)
                .documentLink("abc_test.pdf")
                .aiResult(aiResult)
                .build();
    }

    @Test
    void getMyDocumentById_ownerSeesFullFieldsAndRealSignedUrl() {
        UUID userId = UUID.randomUUID();
        User user = new User();
        user.setId(userId);
        Document doc = buildDoc(userId, UUID.randomUUID(), AI_RESULT_JSON);

        when(userRepository.findByEmailAndIsDeletedFalse("staff1@hcl.com")).thenReturn(Optional.of(user));
        when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));
        when(documentMapper.toResponse(doc)).thenReturn(new DocumentResponse());
        when(supabaseStorageService.generateSignedUrl(any(), any(), anyInt()))
                .thenReturn("https://signed.example/original");

        DocumentResponse response = documentService.getMyDocumentById(doc.getId().toString(), "staff1@hcl.com");

        assertTrue(response.isRequesterIsOwner());
        assertTrue("https://signed.example/original".equals(response.getSignedUrl()));
        assertTrue(response.getAiResult().contains("applicant_name"));
        assertTrue(response.getAiResult().contains("salary"));
    }

    @Test
    void getDepartmentDocumentById_nonOwnerGetsStrippedFieldsAndNoSignedUrl() {
        UUID deptId = UUID.randomUUID();
        UUID managerId = UUID.randomUUID();
        UUID otherStaffId = UUID.randomUUID();

        User manager = new User();
        manager.setId(managerId);
        Department managerDept = new Department();
        managerDept.setId(deptId);
        manager.setDepartment(managerDept);

        Document doc = buildDoc(otherStaffId, deptId, AI_RESULT_JSON);

        when(userRepository.findByEmailAndIsDeletedFalse("manager1@hcl.com")).thenReturn(Optional.of(manager));
        when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));
        when(documentMapper.toResponse(doc)).thenReturn(new DocumentResponse());

        DocumentResponse response = documentService.getDepartmentDocumentById(doc.getId().toString(), "manager1@hcl.com");

        assertFalse(response.isRequesterIsOwner());
        assertNull(response.getSignedUrl());
        assertFalse(response.getAiResult().contains("applicant_name"));
        assertFalse(response.getAiResult().contains("bsb"));
        assertTrue(response.getAiResult().contains("salary")); // not in sensitive_field_keys -- stays
    }

    @Test
    void getDepartmentDocumentById_missingSensitiveFieldKeys_failsClosedStripsAllFields() {
        UUID deptId = UUID.randomUUID();
        UUID managerId = UUID.randomUUID();
        UUID otherStaffId = UUID.randomUUID();

        User manager = new User();
        manager.setId(managerId);
        Department managerDept = new Department();
        managerDept.setId(deptId);
        manager.setDepartment(managerDept);

        String legacyAiResult = "{\"fields\":{\"applicant_name\":\"Jo Worker\"},\"redaction\":{\"type\":\"boxes\",\"items\":[]}}";
        Document doc = buildDoc(otherStaffId, deptId, legacyAiResult);

        when(userRepository.findByEmailAndIsDeletedFalse("manager1@hcl.com")).thenReturn(Optional.of(manager));
        when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));
        when(documentMapper.toResponse(doc)).thenReturn(new DocumentResponse());

        DocumentResponse response = documentService.getDepartmentDocumentById(doc.getId().toString(), "manager1@hcl.com");

        assertFalse(response.getAiResult().contains("applicant_name"));
    }
}
