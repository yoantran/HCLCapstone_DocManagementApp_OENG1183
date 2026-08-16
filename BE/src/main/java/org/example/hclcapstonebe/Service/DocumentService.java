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
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;
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
    private final DocumentSanitizerService documentSanitizerService;

    private static final String BUCKET = "documents";
    private static final int SIGNED_URL_TTL = 3600; // 1 hour in seconds


    private static final Map<DocumentFormatEnum, byte[]> FILE_SIGNATURES = Map.of(
            DocumentFormatEnum.PDF,  new byte[]{0x25, 0x50, 0x44, 0x46},
            DocumentFormatEnum.DOCX, new byte[]{0x50, 0x4B, 0x03, 0x04},
            DocumentFormatEnum.PNG,  new byte[]{(byte) 0x89, 0x50, 0x4E, 0x47},
            DocumentFormatEnum.JPG,  new byte[]{(byte) 0xFF, (byte) 0xD8, (byte) 0xFF},
            DocumentFormatEnum.JPEG, new byte[]{(byte) 0xFF, (byte) 0xD8, (byte) 0xFF}
    );

    // ─── UPLOAD ───────────────────────────────────────────

    public DocumentResponse uploadOne(MultipartFile file, String type, String currentUserEmail,
            BigDecimal proposedRepaymentAmount) {
        User uploader = getUserByEmail(currentUserEmail);
        Document doc = buildAndSaveDocument(file, type, uploader, proposedRepaymentAmount);
        sendNotificationToManager(doc, uploader);
        return toDocumentResponse(doc);
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
            return toDocumentResponse(doc);
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

        switch (format) {
            case PDF -> documentSanitizerService.validatePdfStructure(fileData);
            case DOCX -> documentSanitizerService.validateDocxStructure(fileData);
            case PNG, JPG, JPEG -> fileData = documentSanitizerService.sanitizeImage(fileData, format.name());
            case CSV -> {
                // CSVs do not require structural validation
            }
        }

        // ── Upload to Supabase with UUID prefix (always unique in bucket) ──
        String storagePath = UUID.randomUUID() + "_" + originalName;
        String uploadedPath = supabaseStorageService.uploadFile(BUCKET, fileData, storagePath, file.getContentType());

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
                .map(this::toDocumentResponse)
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
        return toDocumentResponse(doc);
    }

    // ─── VIEW: BOSS ONLY (department docs) ────────────────

    public List<DocumentResponse> getDepartmentDocuments(String currentUserEmail) {
        User boss = getUserByEmail(currentUserEmail);
        return documentRepository
                .findByDepartmentIdAndIsDeletedFalse(boss.getDepartment().getId())
                .stream()
                .map(this::toDocumentResponse)
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
        return toDocumentResponse(doc);
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
    private DocumentResponse toDocumentResponse(Document doc) {
        DocumentResponse response = documentMapper.toResponse(doc);
        response.setScanStatus(doc.getScanStatus());

        boolean accessible = isAccessible(doc);
        response.setAccessible(accessible);

        // only expose signed URL for accessible documents
        if (accessible) {
            String signedUrl = supabaseStorageService.generateSignedUrl(
                    BUCKET, doc.getDocumentLink(), SIGNED_URL_TTL
            );
            response.setSignedUrl(signedUrl);
        }
        return response;
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