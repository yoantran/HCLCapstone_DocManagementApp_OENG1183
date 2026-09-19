package org.example.hclcapstonebe.Service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.example.hclcapstonebe.DTO.Response.DocumentResponse;
import org.example.hclcapstonebe.DTO.Response.RedactedPreviewResponse;
import org.example.hclcapstonebe.Entities.Department;
import org.example.hclcapstonebe.Entities.Document;
import org.example.hclcapstonebe.Entities.User;
import org.example.hclcapstonebe.Enums.DocumentFormatEnum;
import org.example.hclcapstonebe.Enums.RedactedPreviewStatus;
import org.example.hclcapstonebe.Enums.RoleEnum;
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
import org.springframework.core.task.TaskRejectedException;
import org.springframework.http.HttpStatus;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

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
    @Mock private RedactedPreviewService redactedPreviewService;

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
        Department dept = null;
        if (departmentId != null) {
            dept = new Department();
            dept.setId(departmentId);
        }
        return Document.builder()
                .id(UUID.randomUUID())
                .uploader(uploader)
                .department(dept)
                .scanStatus(ScanStatus.CLEAN)
                .documentLink("abc_test.pdf")
                .aiResult(aiResult)
                .build();
    }

    private User buildUser(UUID id, RoleEnum role, UUID departmentId) {
        User user = new User();
        user.setId(id);
        user.setRole(role);
        if (departmentId != null) {
            Department dept = new Department();
            dept.setId(departmentId);
            user.setDepartment(dept);
        }
        return user;
    }

    // ─── 1. UPLOAD OPERATIONS ───────────────────────────────────────────────

    @Test
    void upload_validationAndExecutionFlows() {
        assertAll("Upload Validation Logic",
                () -> {
                    // Empty batch validation
                    List<MultipartFile> emptyList = List.of();
                    AppException ex = assertThrows(AppException.class, () ->
                            documentService.uploadMany(emptyList, "INVOICE", "test@example.com", null));
                    assertEquals(HttpStatus.BAD_REQUEST, ex.getStatus());
                },
                () -> {
                    // Infected file gating
                    User uploader = buildUser(UUID.randomUUID(), RoleEnum.STAFF, null);
                    uploader.setEmail("staff1@hcl.com");
                    when(userRepository.findByEmailAndIsDeletedFalse("staff1@hcl.com")).thenReturn(Optional.of(uploader));
                    when(documentRepository.findByUploaderIdAndIsDeletedFalse(any())).thenReturn(List.of());
                    when(clamAvScannerService.scanStream(any())).thenReturn(
                            new ClamAvScannerService.ScanResult(ScanStatus.INFECTED, "Eicar-Test-Signature")
                    );
                    when(documentRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));
                    when(documentMapper.toResponse(any())).thenReturn(new DocumentResponse());

                    MockMultipartFile infectedFile = new MockMultipartFile("file", "eicar.csv", "text/csv", "fake".getBytes());
                    documentService.uploadOne(infectedFile, "PAY_SLIP", "staff1@hcl.com", null);
                    verify(supabaseStorageService, never()).uploadFile(any(), any(), any(), any());
                },
                () -> {
                    // AI Executor saturated fallback
                    User uploader = buildUser(UUID.randomUUID(), RoleEnum.STAFF, null);
                    uploader.setEmail("staff2@hcl.com"); // <--- FIX: Ensure email is set on user object
                    when(userRepository.findByEmailAndIsDeletedFalse("staff2@hcl.com")).thenReturn(Optional.of(uploader));
                    when(clamAvScannerService.scanStream(any())).thenReturn(
                            new ClamAvScannerService.ScanResult(ScanStatus.CLEAN, "Clean")
                    );
                    when(documentRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));
                    when(documentMapper.toResponse(any())).thenReturn(new DocumentResponse());
                    doThrow(new TaskRejectedException("pool saturated"))
                            .when(aiProcessingService).processAsync(any(), any(), any(), any(), any());

                    MockMultipartFile cleanFile = new MockMultipartFile("file", "clean.csv", "text/csv", "fake".getBytes());
                    assertDoesNotThrow(() -> documentService.uploadOne(cleanFile, "PAY_SLIP", "staff2@hcl.com", null));
                    verify(aiProcessingService).markFailed(any(), eq("staff2@hcl.com"), any());
                }
        );
    }

    // ─── 2. READ OPERATIONS (OWNER vs NON-OWNER) ────────────────────────────

    @Test
    void getMyDocument_ownerAccessAndAccessDenied() {
        UUID userId = UUID.randomUUID();
        User user = buildUser(userId, RoleEnum.STAFF, null);
        Document doc = buildDoc(userId, UUID.randomUUID(), AI_RESULT_JSON);

        when(userRepository.findByEmailAndIsDeletedFalse("owner@hcl.com")).thenReturn(Optional.of(user));
        when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));
        when(documentMapper.toResponse(doc)).thenReturn(new DocumentResponse());
        when(supabaseStorageService.generateSignedUrl(any(), any(), anyInt())).thenReturn("https://signed.example/original");

        DocumentResponse response = documentService.getMyDocumentById(doc.getId().toString(), "owner@hcl.com");
        assertTrue(response.isRequesterIsOwner());
        assertEquals("https://signed.example/original", response.getSignedUrl());

        // Access denied check
        User caller = buildUser(UUID.randomUUID(), RoleEnum.STAFF, null);
        when(userRepository.findByEmailAndIsDeletedFalse("other@hcl.com")).thenReturn(Optional.of(caller));
        assertThrows(AppException.class, () -> documentService.getMyDocumentById(doc.getId().toString(), "other@hcl.com"));
    }

    @Test
    void getDepartmentDocuments_success() {
        String bossEmail = "boss@example.com";
        UUID bossId = UUID.randomUUID();
        UUID deptId = UUID.randomUUID();

        User boss = buildUser(bossId, RoleEnum.MANAGER, deptId);
        boss.setEmail(bossEmail);
        Document doc = buildDoc(bossId, deptId, AI_RESULT_JSON);

        when(userRepository.findByEmailAndIsDeletedFalse(bossEmail)).thenReturn(Optional.of(boss));
        when(documentRepository.findByDepartmentIdAndIsDeletedFalse(deptId)).thenReturn(List.of(doc));
        when(documentMapper.toResponse(any())).thenReturn(new DocumentResponse());
        when(supabaseStorageService.generateSignedUrls(any(), any(), anyInt())).thenReturn(Map.of());

        List<DocumentResponse> results = documentService.getDepartmentDocuments(bossEmail);
        assertNotNull(results);
        assertEquals(1, results.size());
    }

    // ─── 3. AI SENSITIVE FIELD STRIPPING ────────────────────────────────────

    @Test
    void getDepartmentDocumentById_fieldScrubbingAndFallbackCases() {
        UUID deptId = UUID.randomUUID();
        User manager = buildUser(UUID.randomUUID(), RoleEnum.MANAGER, deptId);

        when(userRepository.findByEmailAndIsDeletedFalse("mgr@hcl.com")).thenReturn(Optional.of(manager));
        when(documentMapper.toResponse(any())).thenReturn(new DocumentResponse());

        assertAll("Stripping Sensitive Fields",
                () -> {
                    // Non-owner gets stripped fields
                    Document doc = buildDoc(UUID.randomUUID(), deptId, AI_RESULT_JSON);
                    when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));

                    DocumentResponse res = documentService.getDepartmentDocumentById(doc.getId().toString(), "mgr@hcl.com");
                    JsonNode fields = readTree(res.getAiResult()).get("fields");
                    assertFalse(fields.has("applicant_name"));
                    assertTrue(fields.has("salary"));
                },
                () -> {
                    // Balance Sheet readiness scrubbed
                    String json = """
                        {"fields":{"total_assets":87500},"sensitive_field_keys":[],
                         "balance_sheet_readiness":{"verdict":"READY","checks":{"current_ratio":{"value":2.5,"pass":true}}}}
                        """;
                    Document doc = buildDoc(UUID.randomUUID(), deptId, json);
                    when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));

                    DocumentResponse res = documentService.getDepartmentDocumentById(doc.getId().toString(), "mgr@hcl.com");
                    assertTrue(readTree(res.getAiResult()).get("balance_sheet_readiness").get("checks").get("current_ratio").get("value").isNull());
                },
                () -> {
                    // Malformed JSON fails closed
                    String malformed = "{\"fields\":{},\"sensitive_field_keys\":[],\"loan_readiness\":{\"checks\":\"invalid\"}}";
                    Document doc = buildDoc(UUID.randomUUID(), deptId, malformed);
                    when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));

                    DocumentResponse res = documentService.getDepartmentDocumentById(doc.getId().toString(), "mgr@hcl.com");
                    assertFalse(readTree(res.getAiResult()).has("loan_readiness"));
                },
                () -> {
                    // Missing sensitive keys fails closed
                    String legacy = "{\"fields\":{\"applicant_name\":\"Jo\"}}";
                    Document doc = buildDoc(UUID.randomUUID(), deptId, legacy);
                    when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));

                    DocumentResponse res = documentService.getDepartmentDocumentById(doc.getId().toString(), "mgr@hcl.com");
                    assertFalse(res.getAiResult().contains("Jo"));
                }
        );
    }

    // ─── 4. REDACTED PREVIEW GATEWAYS ────────────────────────────────────────

    @Test
    void getRedactedPreviewStatus_eligibilityGates() {
        UUID deptId = UUID.randomUUID();
        User manager = buildUser(UUID.randomUUID(), RoleEnum.MANAGER, deptId);
        String aiJson = """
                {"fields":{"bsb":"123"},"sensitive_field_keys":["bsb"],
                 "redaction":{"type":"boxes","items":[{"field":"bsb","value":"123"}]}}
                """;

        when(userRepository.findByEmailAndIsDeletedFalse("mgr@hcl.com")).thenReturn(Optional.of(manager));

        assertAll("Format and Eligibility Gates",
                () -> {
                    // Scanned PDF / Image eligible
                    Document doc = buildDoc(UUID.randomUUID(), deptId, aiJson);
                    doc.setFormat(DocumentFormatEnum.PNG);
                    when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));

                    RedactedPreviewResponse res = documentService.getRedactedPreviewStatus(doc.getId().toString(), "mgr@hcl.com", false);
                    assertEquals(RedactedPreviewStatus.GENERATING, res.getStatus());
                },
                () -> {
                    // Wrong department forbidden
                    Document doc = buildDoc(UUID.randomUUID(), UUID.randomUUID(), aiJson);
                    doc.setFormat(DocumentFormatEnum.PNG);
                    when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));

                    assertThrows(AppException.class, () -> documentService.getRedactedPreviewStatus(doc.getId().toString(), "mgr@hcl.com", false));
                },
                () -> {
                    // CSV unsupported
                    Document doc = buildDoc(UUID.randomUUID(), deptId, aiJson);
                    doc.setFormat(DocumentFormatEnum.CSV);
                    when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));

                    AppException ex = assertThrows(AppException.class, () -> documentService.getRedactedPreviewStatus(doc.getId().toString(), "mgr@hcl.com", false));
                    assertEquals(HttpStatus.NOT_IMPLEMENTED, ex.getStatus());
                },
                () -> {
                    // Empty redactions unprocessable
                    Document doc = buildDoc(UUID.randomUUID(), deptId, "{\"redaction\":{\"items\":[]}}");
                    doc.setFormat(DocumentFormatEnum.PNG);
                    when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));

                    AppException ex = assertThrows(AppException.class, () -> documentService.getRedactedPreviewStatus(doc.getId().toString(), "mgr@hcl.com", false));
                    assertEquals(HttpStatus.UNPROCESSABLE_ENTITY, ex.getStatus());
                }
        );
    }

    @Test
    void getRedactedPreviewStatus_textNativeSupport() {
        UUID deptId = UUID.randomUUID();
        User manager = buildUser(UUID.randomUUID(), RoleEnum.MANAGER, deptId);
        String textNative = """
                {"processing_path":"text_native","fields":{"bsb":"123"},
                 "redaction":{"type":"spans","items":[{"field":"bsb","value":"123"}]}}
                """;

        when(userRepository.findByEmailAndIsDeletedFalse("mgr@hcl.com")).thenReturn(Optional.of(manager));

        // PDF text-native
        Document pdfDoc = buildDoc(UUID.randomUUID(), deptId, textNative);
        pdfDoc.setFormat(DocumentFormatEnum.PDF);
        when(documentRepository.findByIdAndIsDeletedFalse(pdfDoc.getId())).thenReturn(Optional.of(pdfDoc));
        assertEquals(RedactedPreviewStatus.GENERATING, documentService.getRedactedPreviewStatus(pdfDoc.getId().toString(), "mgr@hcl.com", false).getStatus());

        // DOCX text-native
        Document docxDoc = buildDoc(UUID.randomUUID(), deptId, textNative);
        docxDoc.setFormat(DocumentFormatEnum.DOCX);
        when(documentRepository.findByIdAndIsDeletedFalse(docxDoc.getId())).thenReturn(Optional.of(docxDoc));
        assertEquals(RedactedPreviewStatus.GENERATING, documentService.getRedactedPreviewStatus(docxDoc.getId().toString(), "mgr@hcl.com", false).getStatus());
    }

    @Test
    void getRedactedPreviewStatus_stateTransitions() {
        UUID deptId = UUID.randomUUID();
        User owner = buildUser(UUID.randomUUID(), RoleEnum.STAFF, deptId);
        String aiJson = "{\"redaction\":{\"items\":[{\"field\":\"a\"}]}}";

        when(userRepository.findByEmailAndIsDeletedFalse("owner@hcl.com")).thenReturn(Optional.of(owner));

        assertAll("Preview State Handling",
                () -> {
                    // READY status
                    Document doc = buildDoc(owner.getId(), deptId, aiJson);
                    doc.setFormat(DocumentFormatEnum.PNG);
                    doc.setRedactedPreviewStatus(RedactedPreviewStatus.READY);
                    doc.setRedactedPreviewPath("path/test.png");

                    when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));
                    when(supabaseStorageService.generateSignedUrl(any(), eq("path/test.png"), anyInt())).thenReturn("https://signed.png");

                    RedactedPreviewResponse res = documentService.getRedactedPreviewStatus(doc.getId().toString(), "owner@hcl.com", false);
                    assertEquals(RedactedPreviewStatus.READY, res.getStatus());
                    assertEquals("https://signed.png", res.getPreviewUrl());
                },
                () -> {
                    // FAILED without retry
                    Document doc = buildDoc(owner.getId(), deptId, aiJson);
                    doc.setFormat(DocumentFormatEnum.PNG);
                    doc.setRedactedPreviewStatus(RedactedPreviewStatus.FAILED);
                    doc.setRedactedPreviewFailureReason("error");

                    when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));
                    RedactedPreviewResponse res = documentService.getRedactedPreviewStatus(doc.getId().toString(), "owner@hcl.com", false);
                    assertEquals(RedactedPreviewStatus.FAILED, res.getStatus());
                },
                () -> {
                    // FAILED with retry flag
                    Document doc = buildDoc(owner.getId(), deptId, aiJson);
                    doc.setFormat(DocumentFormatEnum.PNG);
                    doc.setRedactedPreviewStatus(RedactedPreviewStatus.FAILED);

                    when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));
                    RedactedPreviewResponse res = documentService.getRedactedPreviewStatus(doc.getId().toString(), "owner@hcl.com", true);
                    assertEquals(RedactedPreviewStatus.GENERATING, res.getStatus());
                }
        );
    }

    @Test
    void getRedactedPreviewStatus_executorRejection() {
        UUID deptId = UUID.randomUUID();
        User manager = buildUser(UUID.randomUUID(), RoleEnum.MANAGER, deptId);
        String aiJson = "{\"redaction\":{\"items\":[{\"field\":\"a\"}]}}";

        Document doc = buildDoc(UUID.randomUUID(), deptId, aiJson);
        doc.setFormat(DocumentFormatEnum.PNG);

        when(userRepository.findByEmailAndIsDeletedFalse("mgr@hcl.com")).thenReturn(Optional.of(manager));
        when(documentRepository.findByIdAndIsDeletedFalse(doc.getId())).thenReturn(Optional.of(doc));
        doThrow(new TaskRejectedException("saturated")).when(redactedPreviewService).generateAsync(any(), any(), any());

        RedactedPreviewResponse res = documentService.getRedactedPreviewStatus(doc.getId().toString(), "mgr@hcl.com", false);
        assertEquals(RedactedPreviewStatus.FAILED, res.getStatus());
        verify(redactedPreviewService).markRejected(eq(doc.getId()), eq("mgr@hcl.com"), any());
    }

    // ─── 5. DELETE AUTHORIZATION ─────────────────────────────────────────────

    @Test
    void deleteDocument_roleAuthorizationMatrix() {
        UUID deptId = UUID.randomUUID();
        UUID otherDeptId = UUID.randomUUID();

        User staff = buildUser(UUID.randomUUID(), RoleEnum.STAFF, deptId);
        User manager = buildUser(UUID.randomUUID(), RoleEnum.MANAGER, deptId);
        User admin = buildUser(UUID.randomUUID(), RoleEnum.ADMIN, otherDeptId);

        Document ownDoc = buildDoc(staff.getId(), deptId, AI_RESULT_JSON);
        Document otherDoc = buildDoc(UUID.randomUUID(), deptId, AI_RESULT_JSON);

        assertAll("Delete Operations",
                () -> {
                    // Staff deletes own
                    when(userRepository.findByEmailAndIsDeletedFalse("staff@hcl.com")).thenReturn(Optional.of(staff));
                    when(documentRepository.findByIdAndIsDeletedFalse(ownDoc.getId())).thenReturn(Optional.of(ownDoc));
                    documentService.deleteDocument(ownDoc.getId().toString(), "staff@hcl.com");
                    assertTrue(ownDoc.isDeleted());
                },
                () -> {
                    // Staff deletes other (Forbidden)
                    when(userRepository.findByEmailAndIsDeletedFalse("staff@hcl.com")).thenReturn(Optional.of(staff));
                    when(documentRepository.findByIdAndIsDeletedFalse(otherDoc.getId())).thenReturn(Optional.of(otherDoc));
                    assertThrows(AppException.class, () -> documentService.deleteDocument(otherDoc.getId().toString(), "staff@hcl.com"));
                },
                () -> {
                    // Manager deletes dept document
                    when(userRepository.findByEmailAndIsDeletedFalse("mgr@hcl.com")).thenReturn(Optional.of(manager));
                    when(documentRepository.findByIdAndIsDeletedFalse(otherDoc.getId())).thenReturn(Optional.of(otherDoc));
                    documentService.deleteDocument(otherDoc.getId().toString(), "mgr@hcl.com");
                    assertTrue(otherDoc.isDeleted());
                },
                () -> {
                    // Admin deletes any document
                    when(userRepository.findByEmailAndIsDeletedFalse("admin@hcl.com")).thenReturn(Optional.of(admin));
                    when(documentRepository.findByIdAndIsDeletedFalse(otherDoc.getId())).thenReturn(Optional.of(otherDoc));
                    documentService.deleteDocument(otherDoc.getId().toString(), "admin@hcl.com");
                    assertTrue(otherDoc.isDeleted());
                }
        );
    }

    @Test
    void departmentNullPointerGuards() {
        UUID deptId = UUID.randomUUID();
        User manager = buildUser(UUID.randomUUID(), RoleEnum.MANAGER, deptId);
        manager.setEmail("mgr@hcl.com");

        String validPngAiJson = """
                {"fields":{"bsb":"123"},"sensitive_field_keys":["bsb"],
                 "redaction":{"type":"boxes","items":[{"field":"bsb","value":"123"}]}}
                """;

        User uploaderWithoutDept = new User();
        uploaderWithoutDept.setId(UUID.randomUUID()); // FIX: prevents NPE on doc.getUploader().getId()

        Document deptLessDoc = Document.builder()
                .id(UUID.randomUUID())
                .uploader(uploaderWithoutDept)
                .department(null)     // document has no department
                .scanStatus(ScanStatus.CLEAN)
                .format(DocumentFormatEnum.PNG)
                .aiResult(validPngAiJson)
                .build();

        when(userRepository.findByEmailAndIsDeletedFalse("mgr@hcl.com")).thenReturn(Optional.of(manager));
        when(documentRepository.findByIdAndIsDeletedFalse(deptLessDoc.getId())).thenReturn(Optional.of(deptLessDoc));

        assertAll("Null Department Checks",
                () -> {
                    AppException ex = assertThrows(AppException.class, () ->
                            documentService.deleteDocument(deptLessDoc.getId().toString(), "mgr@hcl.com"));
                    assertEquals(HttpStatus.FORBIDDEN, ex.getStatus());
                },
                () -> {
                    AppException ex = assertThrows(AppException.class, () ->
                            documentService.getRedactedPreviewStatus(deptLessDoc.getId().toString(), "mgr@hcl.com", false));
                    assertEquals(HttpStatus.FORBIDDEN, ex.getStatus());
                }
        );
    }
}