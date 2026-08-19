package org.example.hclcapstonebe.Service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.example.hclcapstonebe.DTO.Response.DocumentResponse;
import org.example.hclcapstonebe.Entities.Department;
import org.example.hclcapstonebe.Entities.Document;
import org.example.hclcapstonebe.Entities.User;
import org.example.hclcapstonebe.Enums.DocumentFormatEnum;
import org.example.hclcapstonebe.Enums.ScanStatus;
import org.example.hclcapstonebe.Exception.AppException;
import org.example.hclcapstonebe.Mapper.DocumentMapper;
import org.example.hclcapstonebe.Repository.DocumentRepository;
import org.example.hclcapstonebe.Repository.NotificationRepository;
import org.example.hclcapstonebe.Repository.UserRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.RestTemplate;

import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.eq;
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
             "redaction":{"type":"boxes","items":[{"field":"bsb","value":"123-456","x_pct":0.1,"y_pct":0.1,"w_pct":0.2,"h_pct":0.1}]},
             "loan_readiness":{"checks":{"min_income":{"value":5000,"pass":true}}}}
            """;

    private static JsonNode readTree(String json) {
        try {
            return new ObjectMapper().readTree(json);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

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

        JsonNode result = readTree(response.getAiResult());
        JsonNode fields = result.get("fields");
        assertFalse(fields.has("applicant_name"));
        assertFalse(fields.has("bsb"));
        assertTrue(fields.has("salary")); // not in sensitive_field_keys -- stays
        // sensitive_field_keys is metadata (field labels only, never values) --
        // it stays in the non-owner response
        assertTrue(result.has("sensitive_field_keys"));

        // The stripped value must not be reachable elsewhere in the blob --
        // redaction.items[].value used to carry the exact same literal.
        assertFalse(response.getAiResult().contains("123-456"));
        assertFalse(result.has("redaction"));
        assertFalse(result.has("preview_image_base64"));

        // Issue #203 -- loan_readiness stays (Manager has a legitimate
        // reason to see the verdict), but checks.*.value is nulled since
        // it re-derives from the same income data fields was scrubbed of.
        assertTrue(result.has("loan_readiness"));
        JsonNode minIncomeCheck = result.get("loan_readiness").get("checks").get("min_income");
        assertTrue(minIncomeCheck.get("value").isNull());
        assertTrue(minIncomeCheck.get("pass").asBoolean());

        // Not present in this fixture at all -- stays absent, not an empty
        // object (nothing to scrub if the key was never there).
        assertFalse(result.has("balance_sheet_readiness"));
    }

    @Test
    void getDepartmentDocumentById_nonOwnerGetsBalanceSheetVerdictWithValuesScrubbed() {
        UUID deptId = UUID.randomUUID();
        UUID managerId = UUID.randomUUID();
        UUID otherStaffId = UUID.randomUUID();

        User manager = new User();
        manager.setId(managerId);
        Department managerDept = new Department();
        managerDept.setId(deptId);
        manager.setDepartment(managerDept);

        String balanceSheetJson = """
                {"fields":{"total_assets":87500},
                 "sensitive_field_keys":[],
                 "balance_sheet_readiness":{"verdict":"READY","checks":{
                     "current_ratio":{"value":2.5,"pass":true,"threshold":1.0},
                     "debt_to_equity":{"value":0.8,"pass":true,"threshold":2.0}}}}
                """;
        Document doc = buildDoc(otherStaffId, deptId, balanceSheetJson);

        when(userRepository.findByEmailAndIsDeletedFalse("manager1@hcl.com")).thenReturn(Optional.of(manager));
        when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));
        when(documentMapper.toResponse(doc)).thenReturn(new DocumentResponse());

        DocumentResponse response = documentService.getDepartmentDocumentById(doc.getId().toString(), "manager1@hcl.com");

        JsonNode result = readTree(response.getAiResult());
        JsonNode readiness = result.get("balance_sheet_readiness");
        assertTrue(readiness.has("verdict"));
        assertEquals("READY", readiness.get("verdict").asText());
        assertTrue(readiness.get("checks").get("current_ratio").get("value").isNull());
        assertTrue(readiness.get("checks").get("current_ratio").get("pass").asBoolean());
        assertTrue(readiness.get("checks").get("debt_to_equity").get("value").isNull());
    }

    @Test
    void getDepartmentDocumentById_malformedReadinessShape_failsClosedRemovesWholeObject() {
        UUID deptId = UUID.randomUUID();
        UUID managerId = UUID.randomUUID();
        UUID otherStaffId = UUID.randomUUID();

        User manager = new User();
        manager.setId(managerId);
        Department managerDept = new Department();
        managerDept.setId(deptId);
        manager.setDepartment(managerDept);

        // "checks" is a string, not an object -- a shape this method
        // doesn't recognize. Must remove loan_readiness entirely rather
        // than risk leaving a raw value un-scrubbed in an unexpected shape.
        String malformedJson = """
                {"fields":{},"sensitive_field_keys":[],
                 "loan_readiness":{"verdict":"READY","checks":"not an object"}}
                """;
        Document doc = buildDoc(otherStaffId, deptId, malformedJson);

        when(userRepository.findByEmailAndIsDeletedFalse("manager1@hcl.com")).thenReturn(Optional.of(manager));
        when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));
        when(documentMapper.toResponse(doc)).thenReturn(new DocumentResponse());

        DocumentResponse response = documentService.getDepartmentDocumentById(doc.getId().toString(), "manager1@hcl.com");

        JsonNode result = readTree(response.getAiResult());
        assertFalse(result.has("loan_readiness"));
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

        String legacyAiResult = "{\"fields\":{\"applicant_name\":\"Jo Worker\"},"
                + "\"redaction\":{\"type\":\"boxes\",\"items\":[{\"field\":\"applicant_name\",\"value\":\"Jo Worker\"}]}}";
        Document doc = buildDoc(otherStaffId, deptId, legacyAiResult);

        when(userRepository.findByEmailAndIsDeletedFalse("manager1@hcl.com")).thenReturn(Optional.of(manager));
        when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));
        when(documentMapper.toResponse(doc)).thenReturn(new DocumentResponse());

        DocumentResponse response = documentService.getDepartmentDocumentById(doc.getId().toString(), "manager1@hcl.com");

        assertFalse(response.getAiResult().contains("applicant_name"));
        assertFalse(response.getAiResult().contains("Jo Worker"));
        JsonNode result = readTree(response.getAiResult());
        assertFalse(result.has("redaction"));
    }

    @Test
    void getRedactedPreview_nonOwnerInDepartment_returnsRedactedBytes() {
        ReflectionTestUtils.setField(documentService, "aiServiceUrl", "http://ai-service:8000");

        UUID deptId = UUID.randomUUID();
        UUID managerId = UUID.randomUUID();
        UUID otherStaffId = UUID.randomUUID();

        User manager = new User();
        manager.setId(managerId);
        Department managerDept = new Department();
        managerDept.setId(deptId);
        manager.setDepartment(managerDept);

        String aiResultWithItems = """
                {"fields":{"bsb":"123-456"},
                 "sensitive_field_keys":["bsb"],
                 "redaction":{"type":"boxes","items":[{"field":"bsb","value":"123-456","x_pct":0.1,"y_pct":0.1,"w_pct":0.2,"h_pct":0.1}]}}
                """;
        Document doc = buildDoc(otherStaffId, deptId, aiResultWithItems);
        doc.setFormat(DocumentFormatEnum.PNG);

        when(userRepository.findByEmailAndIsDeletedFalse("manager1@hcl.com")).thenReturn(Optional.of(manager));
        when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));
        when(supabaseStorageService.downloadFile("documents", "abc_test.pdf")).thenReturn("raw-bytes".getBytes());
        byte[] redactedBytes = "redacted-bytes".getBytes();
        when(restTemplate.exchange(
                eq("http://ai-service:8000/apply-redaction"),
                eq(HttpMethod.POST),
                any(HttpEntity.class),
                eq(byte[].class)
        )).thenReturn(new ResponseEntity<>(redactedBytes, HttpStatus.OK));

        byte[] result = documentService.getRedactedPreview(doc.getId().toString(), "manager1@hcl.com");

        assertArrayEquals(redactedBytes, result);
    }

    @Test
    void getRedactedPreview_ownerWithNoDepartment_succeeds() {
        ReflectionTestUtils.setField(documentService, "aiServiceUrl", "http://ai-service:8000");

        UUID deptId = UUID.randomUUID();
        UUID ownerId = UUID.randomUUID();

        User owner = new User();
        owner.setId(ownerId);
        // owner.department left null -- e.g. ADMIN, or STAFF not yet assigned a department

        String aiResultWithItems = """
                {"fields":{"bsb":"123-456"},
                 "sensitive_field_keys":["bsb"],
                 "redaction":{"type":"boxes","items":[{"field":"bsb","value":"123-456","x_pct":0.1,"y_pct":0.1,"w_pct":0.2,"h_pct":0.1}]}}
                """;
        Document doc = buildDoc(ownerId, deptId, aiResultWithItems);
        doc.setFormat(DocumentFormatEnum.PNG);

        when(userRepository.findByEmailAndIsDeletedFalse("owner1@hcl.com")).thenReturn(Optional.of(owner));
        when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));
        when(supabaseStorageService.downloadFile("documents", "abc_test.pdf")).thenReturn("raw-bytes".getBytes());
        byte[] redactedBytes = "redacted-bytes".getBytes();
        when(restTemplate.exchange(
                eq("http://ai-service:8000/apply-redaction"),
                eq(HttpMethod.POST),
                any(HttpEntity.class),
                eq(byte[].class)
        )).thenReturn(new ResponseEntity<>(redactedBytes, HttpStatus.OK));

        byte[] result = documentService.getRedactedPreview(doc.getId().toString(), "owner1@hcl.com");

        assertArrayEquals(redactedBytes, result);
    }

    @Test
    void getRedactedPreview_wrongDepartment_isForbidden() {
        UUID deptId = UUID.randomUUID();
        UUID otherDeptId = UUID.randomUUID();
        UUID managerId = UUID.randomUUID();
        UUID otherStaffId = UUID.randomUUID();

        User manager = new User();
        manager.setId(managerId);
        Department managerDept = new Department();
        managerDept.setId(otherDeptId);
        manager.setDepartment(managerDept);

        Document doc = buildDoc(otherStaffId, deptId, AI_RESULT_JSON);
        doc.setFormat(DocumentFormatEnum.PNG);

        when(userRepository.findByEmailAndIsDeletedFalse("manager1@hcl.com")).thenReturn(Optional.of(manager));
        when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));

        AppException ex = assertThrows(AppException.class, () ->
                documentService.getRedactedPreview(doc.getId().toString(), "manager1@hcl.com"));
        assertEquals(HttpStatus.FORBIDDEN, ex.getStatus());
    }

    @Test
    void getRedactedPreview_pdfFormat_failsClosedNotImplemented() {
        UUID deptId = UUID.randomUUID();
        UUID managerId = UUID.randomUUID();
        UUID otherStaffId = UUID.randomUUID();

        User manager = new User();
        manager.setId(managerId);
        Department managerDept = new Department();
        managerDept.setId(deptId);
        manager.setDepartment(managerDept);

        Document doc = buildDoc(otherStaffId, deptId, AI_RESULT_JSON);
        doc.setFormat(DocumentFormatEnum.PDF);

        when(userRepository.findByEmailAndIsDeletedFalse("manager1@hcl.com")).thenReturn(Optional.of(manager));
        when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));

        AppException ex = assertThrows(AppException.class, () ->
                documentService.getRedactedPreview(doc.getId().toString(), "manager1@hcl.com"));
        assertEquals(HttpStatus.NOT_IMPLEMENTED, ex.getStatus());
    }

    @Test
    void getRedactedPreview_scannedPdf_returnsRedactedBytes() {
        // Issue #207 -- a scanned PDF (processing_path == "ocr") already
        // has real box coordinates from the OCR path at upload time, so
        // it must get a preview too, same as PNG/JPG/JPEG.
        ReflectionTestUtils.setField(documentService, "aiServiceUrl", "http://ai-service:8000");

        UUID deptId = UUID.randomUUID();
        UUID managerId = UUID.randomUUID();
        UUID otherStaffId = UUID.randomUUID();

        User manager = new User();
        manager.setId(managerId);
        Department managerDept = new Department();
        managerDept.setId(deptId);
        manager.setDepartment(managerDept);

        String scannedPdfResult = """
                {"processing_path":"ocr",
                 "fields":{"bsb":"123-456"},
                 "sensitive_field_keys":["bsb"],
                 "redaction":{"type":"boxes","items":[{"field":"bsb","value":"123-456","x_pct":0.1,"y_pct":0.1,"w_pct":0.2,"h_pct":0.1}]}}
                """;
        Document doc = buildDoc(otherStaffId, deptId, scannedPdfResult);
        doc.setFormat(DocumentFormatEnum.PDF);

        when(userRepository.findByEmailAndIsDeletedFalse("manager1@hcl.com")).thenReturn(Optional.of(manager));
        when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));
        when(supabaseStorageService.downloadFile("documents", "abc_test.pdf")).thenReturn("raw-bytes".getBytes());
        byte[] redactedBytes = "redacted-bytes".getBytes();
        when(restTemplate.exchange(
                eq("http://ai-service:8000/apply-redaction"),
                eq(HttpMethod.POST),
                any(HttpEntity.class),
                eq(byte[].class)
        )).thenReturn(new ResponseEntity<>(redactedBytes, HttpStatus.OK));

        byte[] result = documentService.getRedactedPreview(doc.getId().toString(), "manager1@hcl.com");

        assertArrayEquals(redactedBytes, result);
    }

    @Test
    void getRedactedPreview_textNativePdf_stillFailsClosedNotImplemented() {
        // A real text-native PDF (processing_path == "text_native") has
        // no image to draw boxes on -- #207 only widens the gate for
        // scanned PDFs, this case stays 501 same as before (#208 backlog).
        UUID deptId = UUID.randomUUID();
        UUID managerId = UUID.randomUUID();
        UUID otherStaffId = UUID.randomUUID();

        User manager = new User();
        manager.setId(managerId);
        Department managerDept = new Department();
        managerDept.setId(deptId);
        manager.setDepartment(managerDept);

        String textNativePdfResult = """
                {"processing_path":"text_native",
                 "fields":{"bsb":"123-456"},
                 "sensitive_field_keys":["bsb"],
                 "redaction":{"type":"spans","items":[{"field":"bsb","value":"123-456","start":10,"end":17}]}}
                """;
        Document doc = buildDoc(otherStaffId, deptId, textNativePdfResult);
        doc.setFormat(DocumentFormatEnum.PDF);

        when(userRepository.findByEmailAndIsDeletedFalse("manager1@hcl.com")).thenReturn(Optional.of(manager));
        when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));

        AppException ex = assertThrows(AppException.class, () ->
                documentService.getRedactedPreview(doc.getId().toString(), "manager1@hcl.com"));
        assertEquals(HttpStatus.NOT_IMPLEMENTED, ex.getStatus());
    }

    @Test
    void getRedactedPreview_noRedactionItems_failsClosedUnprocessable() {
        UUID deptId = UUID.randomUUID();
        UUID managerId = UUID.randomUUID();
        UUID otherStaffId = UUID.randomUUID();

        User manager = new User();
        manager.setId(managerId);
        Department managerDept = new Department();
        managerDept.setId(deptId);
        manager.setDepartment(managerDept);

        String noItemsResult = """
                {"fields":{"bsb":"123-456"},"sensitive_field_keys":["bsb"],"redaction":{"type":"boxes","items":[]}}
                """;
        Document doc = buildDoc(otherStaffId, deptId, noItemsResult);
        doc.setFormat(DocumentFormatEnum.PNG);

        when(userRepository.findByEmailAndIsDeletedFalse("manager1@hcl.com")).thenReturn(Optional.of(manager));
        when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));

        AppException ex = assertThrows(AppException.class, () ->
                documentService.getRedactedPreview(doc.getId().toString(), "manager1@hcl.com"));
        assertEquals(HttpStatus.UNPROCESSABLE_ENTITY, ex.getStatus());
    }
}
