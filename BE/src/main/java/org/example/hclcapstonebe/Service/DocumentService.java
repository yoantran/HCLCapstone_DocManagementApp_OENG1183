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
import java.time.LocalDateTime;
import java.util.List;
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

    private static final String BUCKET = "documents";
    private static final int SIGNED_URL_TTL = 3600; // 1 hour in seconds

    // ─── UPLOAD ───────────────────────────────────────────

    public DocumentResponse uploadOne(MultipartFile file, String type, String currentUserEmail) {
        User uploader = getUserByEmail(currentUserEmail);
        Document doc = buildAndSaveDocument(file, type, uploader);
        sendNotificationToManager(doc, uploader);
        return toDocumentResponse(doc);
    }

    public List<DocumentResponse> uploadMany(List<MultipartFile> files, String type,
            String currentUserEmail) {
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
            Document doc = buildAndSaveDocument(file, type, uploader);
            sendNotificationToManager(doc, uploader);
            return toDocumentResponse(doc);
        }).collect(Collectors.toList());
    }

    private Document buildAndSaveDocument(MultipartFile file, String type, User uploader) {
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
        try (InputStream rawStream = file.getInputStream();
             BufferedInputStream bis = new BufferedInputStream(rawStream)) {

            bis.mark(8192);
            byte[] header = new byte[4];
            int bytesRead = bis.read(header);

            if (!ext.equals("PDF") && !ext.equals("DOCX") && !ext.equals("CSV")) {
                throw new AppException("Invalid structural file signature match detected", HttpStatus.BAD_REQUEST);
            }

            if (ext.equals("PDF")) {
                if (bytesRead < 4 || header[0] != 0x25 || header[1] != 0x50 || header[2] != 0x44 || header[3] != 0x46) {
                    throw new AppException("Invalid structural file signature match detected", HttpStatus.BAD_REQUEST);
                }
            } else if (ext.equals("DOCX")) {
                if (bytesRead < 4 || header[0] != 0x50 || header[1] != 0x4B || header[2] != 0x03 || header[3] != 0x04) {
                    throw new AppException("Invalid structural file signature match detected", HttpStatus.BAD_REQUEST);
                }
            }

            bis.reset();

            scanResult = clamAvScannerService.scanStream(bis);
            scannedAt = LocalDateTime.now();

        } catch (IOException e) {
            throw new AppException("Failed to process file stream: " + e.getMessage(), HttpStatus.INTERNAL_SERVER_ERROR);
        }

        try {
            fileData = file.getBytes();
        } catch (IOException e) {
            throw new AppException("Failed to read file bytes: " + e.getMessage(), HttpStatus.INTERNAL_SERVER_ERROR);
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
                .build();

        return documentRepository.save(doc);
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
}