package org.example.hclcapstonebe.Service;

import org.example.hclcapstonebe.DTO.Response.DocumentResponse;
import org.example.hclcapstonebe.Entities.Department;
import org.example.hclcapstonebe.Entities.Document;
import org.example.hclcapstonebe.Entities.Notification;
import org.example.hclcapstonebe.Entities.User;

import org.example.hclcapstonebe.Enums.DocumentFormatEnum;
import org.example.hclcapstonebe.Enums.DocumentTypeEnum;
import org.example.hclcapstonebe.Enums.ScanStatus;
import org.example.hclcapstonebe.Exception.AppException;
import org.example.hclcapstonebe.Exception.InvalidFileSignatureException;
import org.example.hclcapstonebe.Mapper.DocumentMapper;
import org.example.hclcapstonebe.Repository.DocumentRepository;
import org.example.hclcapstonebe.Repository.NotificationRepository;
import org.example.hclcapstonebe.Repository.UserRepository;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.io.BufferedInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class DocumentService {

    private final DocumentRepository documentRepository;
    private final UserRepository userRepository;
    private final NotificationRepository notificationRepository;
    private final SimpMessagingTemplate messagingTemplate;
    private final DocumentMapper documentMapper;
    private final SupabaseStorageService supabaseStorageService;
    private final ClamAvScannerService clamAvScannerService;
    private final AiProcessingService aiProcessingService;
    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Value("${ai.service.url}")
    private String aiServiceUrl;

    private static final String BUCKET = "documents";
    private static final int SIGNED_URL_TTL = 3600; // 1 hour in seconds


    private static final Map<DocumentFormatEnum, byte[]> FILE_SIGNATURES = Map.of(
            DocumentFormatEnum.PDF,  new byte[]{0x25, 0x50, 0x44, 0x46},
            DocumentFormatEnum.DOCX, new byte[]{0x50, 0x4B, 0x03, 0x04},
            DocumentFormatEnum.PNG,  new byte[]{(byte) 0x89, 0x50, 0x4E, 0x47},
            DocumentFormatEnum.JPG,  new byte[]{(byte) 0xFF, (byte) 0xD8, (byte) 0xFF},
            DocumentFormatEnum.JPEG, new byte[]{(byte) 0xFF, (byte) 0xD8, (byte) 0xFF}
    );

    // Storage MIME type keyed off the magic-byte-validated format, never the
    // client-supplied Content-Type header -- a client sending a generic
    // application/octet-stream (curl, Postman, some non-browser clients)
    // otherwise gets rejected by Supabase Storage's bucket mime allowlist
    // with a raw leaked-upstream 500, even though the file itself is a
    // genuinely valid DOCX/PDF/etc per the signature check above.
    private static final Map<DocumentFormatEnum, String> MIME_TYPES = Map.of(
            DocumentFormatEnum.PDF,  "application/pdf",
            DocumentFormatEnum.DOCX, "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            DocumentFormatEnum.CSV,  "text/csv",
            DocumentFormatEnum.PNG,  "image/png",
            DocumentFormatEnum.JPEG, "image/jpeg",
            DocumentFormatEnum.JPG,  "image/jpeg"
    );

    // ─── UPLOAD ───────────────────────────────────────────

    public DocumentResponse uploadOne(MultipartFile file, String type, String currentUserEmail,
            BigDecimal proposedRepaymentAmount) {
        User uploader = getUserByEmail(currentUserEmail);
        Document doc = buildAndSaveDocument(file, type, uploader, proposedRepaymentAmount);
        sendNotificationToManager(doc, uploader);
        return toDocumentResponse(doc, uploader.getId());
    }

    public List<DocumentResponse> uploadMany(List<MultipartFile> files, String type,
            String currentUserEmail, BigDecimal proposedRepaymentAmount) {
        // ── Batch size validation ─────────────────────────────────────────────
        if (files == null || files.isEmpty()) {
            throw new AppException("No files provided", HttpStatus.BAD_REQUEST);
        }
        if (files.size() > 10) {
            throw new AppException(
                    "Batch upload limit exceeded — maximum 10 documents per request, got " + files.size(),
                    HttpStatus.BAD_REQUEST);
        }

        User uploader = getUserByEmail(currentUserEmail);
        return files.stream().map(file -> {
            Document doc = buildAndSaveDocument(file, type, uploader, proposedRepaymentAmount);
            sendNotificationToManager(doc, uploader);
            return toDocumentResponse(doc, uploader.getId());
        }).collect(Collectors.toList());
    }

    private Document buildAndSaveDocument(MultipartFile file, String type, User uploader,
            BigDecimal proposedRepaymentAmount) {
        String originalName = file.getOriginalFilename() != null
                ? file.getOriginalFilename()
                : "unnamed";

        String ext = originalName.contains(".")
                ? originalName.substring(originalName.lastIndexOf('.') + 1).toUpperCase()
                : "PDF";

        String baseName = originalName.contains(".")
                ? originalName.substring(0, originalName.lastIndexOf('.'))
                : originalName;

        // ── Deduplicate filename for this user ──────────────────
        String finalName = resolveUniqueFileName(baseName, ext, UUID.fromString(String.valueOf(uploader.getId())));

        // ── Validation Pipeline ──
        ClamAvScannerService.ScanResult scanResult;
        LocalDateTime scannedAt;
        byte[] fileData;
        DocumentFormatEnum format;

        try (InputStream rawStream = file.getInputStream();
             BufferedInputStream bis = new BufferedInputStream(rawStream)
        ) {
            bis.mark(8192);

            byte[] header = new byte[4];
            int bytesRead = bis.read(header);

            format = parseDocumentFormat(ext);
            validateFileSignature(format, header, bytesRead);

            bis.reset();

            scanResult = clamAvScannerService.scanStream(bis);
            scannedAt = LocalDateTime.now();

        } catch (IOException e) {
            throw new AppException(
                    "Failed to process file stream: " + e.getMessage(),
                    HttpStatus.INTERNAL_SERVER_ERROR
            );
        }

        try {
            fileData = file.getBytes();
        } catch (IOException e) {
            throw new AppException("Failed to read file bytes: " + e.getMessage(), HttpStatus.INTERNAL_SERVER_ERROR);
        }

        // ── Upload to Supabase with UUID prefix (always unique in bucket) ──
        String storagePath = UUID.randomUUID() + "_" + originalName;
        String uploadedPath = supabaseStorageService.uploadFile(BUCKET, fileData, storagePath, MIME_TYPES.get(format));

        Document doc = Document.builder()
                .name(finalName)
                .documentLink(uploadedPath)
                .type(DocumentTypeEnum.valueOf(type.toUpperCase()))
                .format(DocumentFormatEnum.valueOf(ext))
                .byteSize(file.getSize())
                .uploadedDateTime(LocalDateTime.now())
                .uploader(uploader)
                .department(uploader.getDepartment())
                .scanStatus(scanResult.status())
                .scanMessage(scanResult.message())
                .scannedAt(scannedAt)
                .proposedRepaymentAmount(proposedRepaymentAmount)
                .build();

        Document saved = documentRepository.save(doc);

        if (scanResult.status() == ScanStatus.CLEAN) {
            aiProcessingService.processAsync(saved.getId(), fileData, originalName,
                    proposedRepaymentAmount, uploader.getEmail());
        }

        return saved;
    }

    /**
     * Checks existing non-deleted documents for this uploader.
     * If "hello.pdf" exists → returns "hello (1).pdf"
     * If "hello (1).pdf" also exists → returns "hello (2).pdf" etc.
     */
    private String resolveUniqueFileName(String baseName, String ext, UUID uploaderId) {
        // Fetch all non-deleted doc names for this user
        List<String> existingNames = documentRepository
                .findByUploaderIdAndIsDeletedFalse(uploaderId)
                .stream()
                .map(Document::getName)
                .toList();

        String candidate = baseName + "." + ext.toLowerCase();

        if (!existingNames.contains(candidate)) {
            return candidate;
        }

        // Try hello (1).pdf, hello (2).pdf ...
        int counter = 1;
        while (true) {
            candidate = baseName + " (" + counter + ")." + ext.toLowerCase();
            if (!existingNames.contains(candidate)) {
                return candidate;
            }
            counter++;
        }
    }

    // ─── VIEW: STAFF + BOSS (own docs) ────────────────────

    public List<DocumentResponse> getMyDocuments(String currentUserEmail) {
        User user = getUserByEmail(currentUserEmail);
        return documentRepository.findByUploaderIdAndIsDeletedFalse(user.getId())
                .stream()
                .map(doc -> toDocumentResponse(doc, user.getId()))
                .collect(Collectors.toList());
    }

    public DocumentResponse getMyDocumentById(String docId, String currentUserEmail) {
        User user = getUserByEmail(currentUserEmail);
        Document doc = getDocumentOrThrow(docId);

        if (!doc.getUploader().getId().equals(user.getId())) {
            throw new AppException("Access denied", HttpStatus.FORBIDDEN);
        }

        doc.setLatestViewedDateTime(LocalDateTime.now());
        documentRepository.save(doc);
        return toDocumentResponse(doc, user.getId());
    }

    // ─── VIEW: BOSS ONLY (department docs) ────────────────

    public List<DocumentResponse> getDepartmentDocuments(String currentUserEmail) {
        User boss = getUserByEmail(currentUserEmail);
        return documentRepository
                .findByDepartmentIdAndIsDeletedFalse(boss.getDepartment().getId())
                .stream()
                .map(doc -> toDocumentResponse(doc, boss.getId()))
                .collect(Collectors.toList());
    }

    public DocumentResponse getDepartmentDocumentById(String docId, String currentUserEmail) {
        User boss = getUserByEmail(currentUserEmail);
        Document doc = getDocumentOrThrow(docId);

        if (!doc.getDepartment().getId().equals(boss.getDepartment().getId())) {
            throw new AppException("Access denied", HttpStatus.FORBIDDEN);
        }

        doc.setLatestViewedDateTime(LocalDateTime.now());
        documentRepository.save(doc);
        return toDocumentResponse(doc, boss.getId());
    }

    // ─── REDACTED PREVIEW: NON-OWNER VIEWING ──────────────

    /**
     * Returns a redacted rendering of the document for a non-owner viewer.
     * Never falls back to the raw original -- fails closed if the format
     * has no renderable page (CSV) or if redaction.items is missing/empty.
     *
     * A PDF gets a preview if it went through the OCR path at upload time
     * (aiResult.processing_path == "ocr", a genuinely scanned PDF -- issue
     * #207) since that case already has real box coordinates. A PDF or
     * DOCX that went through the text-native path (issue #208) also gets a
     * preview now -- AI's /apply-redaction renders the page itself (via
     * LibreOffice for DOCX) and resolves each stored span's box by
     * searching the rendered page's own text layer, so no box coordinates
     * need to exist ahead of time. CSV still 501s -- no renderable page
     * exists for a spreadsheet at all.
     */
    public byte[] getRedactedPreview(String docId, String currentUserEmail) {
        User requester = getUserByEmail(currentUserEmail);
        Document doc = getDocumentOrThrow(docId);

        if (!isAccessible(doc)) {
            throw new AppException("Document is not accessible", HttpStatus.FORBIDDEN);
        }

        boolean isOwner = doc.getUploader().getId().equals(requester.getId());
        boolean sameDepartment = !isOwner
                && requester.getDepartment() != null
                && doc.getDepartment().getId().equals(requester.getDepartment().getId());
        if (!isOwner && !sameDepartment) {
            throw new AppException("Access denied", HttpStatus.FORBIDDEN);
        }

        boolean isImageFormat = doc.getFormat() == DocumentFormatEnum.PNG
                || doc.getFormat() == DocumentFormatEnum.JPG
                || doc.getFormat() == DocumentFormatEnum.JPEG;
        boolean isScannedPdf = doc.getFormat() == DocumentFormatEnum.PDF
                && "ocr".equals(extractProcessingPath(doc.getAiResult()));
        boolean isTextNativeRenderable = (doc.getFormat() == DocumentFormatEnum.PDF
                || doc.getFormat() == DocumentFormatEnum.DOCX)
                && "text_native".equals(extractProcessingPath(doc.getAiResult()));
        if (!isImageFormat && !isScannedPdf && !isTextNativeRenderable) {
            throw new AppException(
                    "Redacted preview not yet implemented for " + doc.getFormat() + " documents",
                    HttpStatus.NOT_IMPLEMENTED
            );
        }

        JsonNode redactionItems = extractRedactionItems(doc.getAiResult());
        if (redactionItems == null || !redactionItems.isArray() || redactionItems.isEmpty()) {
            throw new AppException("Document has no redaction data yet", HttpStatus.UNPROCESSABLE_ENTITY);
        }

        byte[] originalBytes = supabaseStorageService.downloadFile(BUCKET, doc.getDocumentLink());
        return callApplyRedaction(originalBytes, doc.getName(), redactionItems);
    }

    private JsonNode extractRedactionItems(String aiResultJson) {
        if (aiResultJson == null) {
            return null;
        }
        try {
            JsonNode root = objectMapper.readTree(aiResultJson);
            JsonNode redaction = root.get("redaction");
            return redaction != null ? redaction.get("items") : null;
        } catch (JsonProcessingException e) {
            return null;
        }
    }

    private String extractProcessingPath(String aiResultJson) {
        if (aiResultJson == null) {
            return null;
        }
        try {
            JsonNode root = objectMapper.readTree(aiResultJson);
            JsonNode processingPath = root.get("processing_path");
            return processingPath != null && processingPath.isTextual() ? processingPath.asText() : null;
        } catch (JsonProcessingException e) {
            return null;
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
        try {
            ResponseEntity<byte[]> response = restTemplate.exchange(
                    aiServiceUrl + "/apply-redaction", HttpMethod.POST, request, byte[].class
            );
            if (!response.getStatusCode().is2xxSuccessful() || response.getBody() == null) {
                throw new AppException("AI apply-redaction failed: " + response.getStatusCode(),
                        HttpStatus.INTERNAL_SERVER_ERROR);
            }
            return response.getBody();
        } catch (AppException e) {
            throw e;
        } catch (Exception e) {
            throw new AppException("AI apply-redaction error: " + e.getMessage(), HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    // ─── DELETE: BOSS ONLY ────────────────────────────────

    public void deleteDocument(String docId, String currentUserEmail) {
        User boss = getUserByEmail(currentUserEmail);
        Document doc = getDocumentOrThrow(docId);

        if (!doc.getDepartment().getId().equals(boss.getDepartment().getId())) {
            throw new AppException("Access denied", HttpStatus.FORBIDDEN);
        }

        // Soft delete only — file stays in Supabase bucket
        doc.setDeleted(true);
        doc.setDeletedAt(LocalDateTime.now());
        documentRepository.save(doc);
    }

    // ─── WEBSOCKET NOTIFICATION ───────────────────────────

    private void sendNotificationToManager(Document doc, User uploader) {
        Department dept = uploader.getDepartment();
        if (dept == null || dept.getManager() == null)
            return;

        if (dept.getManager().getId().equals(uploader.getId()))
            return;

        User manager = dept.getManager();
        String content = uploader.getName() + " uploaded a new document: " + doc.getName();

        Notification notification = Notification.builder()
                .triggeredDocument(doc)
                .content(content)
                .receiver(manager)
                .build();

        notificationRepository.save(notification);

        java.util.Map<String, Object> wsPayload = new java.util.HashMap<>();
        wsPayload.put("id", notification.getId());
        wsPayload.put("content", content);
        wsPayload.put("documentId", doc.getId());
        wsPayload.put("documentName", doc.getName());
        wsPayload.put("hasRead", false);
        wsPayload.put("createdAt", java.time.LocalDateTime.now().toString());

        messagingTemplate.convertAndSendToUser(
                manager.getEmail(),
                "/queue/notifications",
                wsPayload);
    }

    // ─── HELPERS ──────────────────────────────────────────

    /**
     * Maps a Document to a response DTO and attaches a fresh signed URL.
     * The signed URL lets the FE read the file directly from Supabase for
     * SIGNED_URL_TTL seconds.
     */
    private DocumentResponse toDocumentResponse(Document doc, UUID requesterId) {
        DocumentResponse response = documentMapper.toResponse(doc);
        response.setScanStatus(doc.getScanStatus());

        boolean accessible = isAccessible(doc);
        response.setAccessible(accessible);

        boolean isOwner = doc.getUploader().getId().equals(requesterId);
        response.setRequesterIsOwner(isOwner);

        // Only the owner gets a real signed URL to the unredacted original --
        // non-owner (e.g. a Manager reviewing a department document) uses
        // /documents/{id}/redacted-preview instead.
        if (accessible && isOwner) {
            String signedUrl = supabaseStorageService.generateSignedUrl(
                    BUCKET, doc.getDocumentLink(), SIGNED_URL_TTL
            );
            response.setSignedUrl(signedUrl);
        }

        // Set explicitly for both branches -- don't rely on documentMapper's
        // implicit same-name passthrough for the owner case, so this method's
        // behavior doesn't depend on mapper internals (and is directly unit
        // -testable with a mocked documentMapper, which returns an empty
        // DocumentResponse and therefore never carries doc.aiResult on its own).
        response.setAiResult(isOwner ? doc.getAiResult() : stripSensitiveFields(doc.getAiResult()));

        return response;
    }

    /**
     * Removes sensitive_field_keys-listed keys from aiResult.fields for a
     * non-owner viewer. Fails closed: if sensitive_field_keys is missing
     * (older aiResult predating this contract) or the JSON can't be parsed,
     * strips the entire fields object rather than risk leaking an unknown
     * raw value.
     *
     * redaction and preview_image_base64 are removed wholesale -- FE has no
     * legitimate use for either (redaction.items[].value is the literal
     * matched string per detected region; preview_image_base64, when ever
     * populated, is the unredacted enhanced document) and BE already reads
     * redaction server-side inside getRedactedPreview.
     *
     * loan_readiness/balance_sheet_readiness are kept (issue #203) -- a
     * Manager reviewing a colleague's document has a legitimate reason to
     * see the READY/NOT_READY verdict -- but every checks.*.value is
     * nulled out first, since those values re-derive from the exact same
     * income/balance-sheet data fields is being scrubbed of. Unexpected
     * shape (missing/malformed "checks") fails closed by removing the
     * whole readiness object rather than risk leaving a raw value in a
     * shape this method doesn't recognize.
     */
    private String stripSensitiveFields(String aiResultJson) {
        if (aiResultJson == null) {
            return null;
        }
        try {
            JsonNode root = objectMapper.readTree(aiResultJson);
            if (!(root instanceof ObjectNode rootObj)) {
                return null;
            }
            JsonNode fieldsNode = rootObj.get("fields");
            JsonNode sensitiveKeysNode = rootObj.get("sensitive_field_keys");
            if (fieldsNode instanceof ObjectNode fieldsObj
                    && sensitiveKeysNode != null && sensitiveKeysNode.isArray()) {
                for (JsonNode keyNode : sensitiveKeysNode) {
                    fieldsObj.remove(keyNode.asText());
                }
            } else if (fieldsNode != null) {
                rootObj.putNull("fields");
            }
            rootObj.remove(List.of("redaction", "preview_image_base64"));
            scrubReadinessCheckValues(rootObj, "loan_readiness");
            scrubReadinessCheckValues(rootObj, "balance_sheet_readiness");
            return objectMapper.writeValueAsString(rootObj);
        } catch (JsonProcessingException e) {
            return null;
        }
    }

    /**
     * Nulls every checks.*.value inside root[key] (loan_readiness or
     * balance_sheet_readiness), keeping verdict/pass/threshold intact.
     * Fails closed on an unexpected shape: removes the whole object
     * rather than risk leaving a raw value un-scrubbed.
     */
    private void scrubReadinessCheckValues(ObjectNode root, String key) {
        JsonNode node = root.get(key);
        if (node == null || node.isNull()) {
            return;
        }
        if (!(node instanceof ObjectNode readinessObj) || !(readinessObj.get("checks") instanceof ObjectNode checksObj)) {
            root.remove(key);
            return;
        }
        for (JsonNode checkNode : checksObj) {
            if (checkNode instanceof ObjectNode checkObj) {
                checkObj.putNull("value");
            } else {
                root.remove(key);
                return;
            }
        }
    }

    private boolean isAccessible(Document doc) {
        return doc.getScanStatus() == null
                || doc.getScanStatus() == ScanStatus.CLEAN;
    }

    private User getUserByEmail(String email) {
        return userRepository.findByEmailAndIsDeletedFalse(email)
                .orElseThrow(() -> new AppException("User not found", HttpStatus.NOT_FOUND));
    }

    private Document getDocumentOrThrow(String docId) {
        return documentRepository.findByIdAndIsDeletedFalse(UUID.fromString(docId))
                .orElseThrow(() -> new AppException("Document not found", HttpStatus.NOT_FOUND));
    }

    private DocumentFormatEnum parseDocumentFormat(String ext) {
        try {
            return DocumentFormatEnum.valueOf(ext.toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException ex) {
            throw new AppException(
                    "Unsupported document format",
                    HttpStatus.BAD_REQUEST
            );
        }
    }

    private void validateFileSignature(DocumentFormatEnum format, byte[] header, int bytesRead) {
        // CSV has no reliable binary signature.
        if (format == DocumentFormatEnum.CSV) {
            return;
        }

        byte[] expected = FILE_SIGNATURES.get(format);

        if (expected == null) {
            throw new AppException(
                    "Unsupported document format",
                    HttpStatus.BAD_REQUEST
            );
        }

        if (bytesRead < expected.length) {
            throw new InvalidFileSignatureException();
        }

        for (int i = 0; i < expected.length; i++) {
            if (header[i] != expected[i]) {
                throw new InvalidFileSignatureException();
            }
        }
    }
}