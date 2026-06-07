package org.example.hclcapstonebe.Service;


import org.example.hclcapstonebe.DTO.Response.DocumentResponse;
import org.example.hclcapstonebe.Entities.Department;
import org.example.hclcapstonebe.Entities.Document;
import org.example.hclcapstonebe.Entities.Notification;
import org.example.hclcapstonebe.Entities.User;

import org.example.hclcapstonebe.Enums.DocumentFormatEnum;
import org.example.hclcapstonebe.Enums.DocumentTypeEnum;
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

import java.time.LocalDateTime;
import java.util.List;
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
    private final DocumentMapper documentMapper;            // MapStruct

    // ─── UPLOAD ───────────────────────────────────────────

    public DocumentResponse uploadOne(MultipartFile file, String type, String currentUserEmail) {
        User uploader = getUserByEmail(currentUserEmail);
        Document doc = buildAndSaveDocument(file, type, uploader);
        sendNotificationTomanager(doc, uploader);
        return documentMapper.toResponse(doc);              // MapStruct
    }

    public List<DocumentResponse> uploadMany(List<MultipartFile> files, String type,
                                             String currentUserEmail) {
        User uploader = getUserByEmail(currentUserEmail);
        return files.stream().map(file -> {
            Document doc = buildAndSaveDocument(file, type, uploader);
            sendNotificationTomanager(doc, uploader);
            return documentMapper.toResponse(doc);          // MapStruct
        }).collect(Collectors.toList());
    }

    private Document buildAndSaveDocument(MultipartFile file, String type, User uploader) {
        String originalName = file.getOriginalFilename();
        String ext = (originalName != null && originalName.contains("."))
                ? originalName.substring(originalName.lastIndexOf('.') + 1).toUpperCase()
                : "PDF";

        // TODO: replace with real S3 upload, store returned URL in fileLink
        String fileLink = "uploads/" + UUID.randomUUID() + "_" + originalName;

        Document doc = Document.builder()
                .name(originalName)
                .documentLink(fileLink)
                .type(DocumentTypeEnum.valueOf(type.toUpperCase()))
                .format(DocumentFormatEnum.valueOf(ext))
                .size(file.getSize())
                .uploader(uploader)
                .department(uploader.getDepartment())
                .build();

        return documentRepository.save(doc);
    }

    // ─── VIEW: STAFF + manager (own docs) ────────────────────

    public List<DocumentResponse> getMyDocuments(String currentUserEmail) {
        User user = getUserByEmail(currentUserEmail);
        return documentRepository.findByUploaderIdAndIsDeletedFalse(user.getId())
                .stream()
                .map(documentMapper::toResponse)            // MapStruct method reference
                .collect(Collectors.toList());
    }

    public DocumentResponse getMyDocumentById(String docId, String currentUserEmail) {
        User user = getUserByEmail(currentUserEmail);
        Document doc = getDocumentOrThrow(docId);

        // RBAC: must be the uploader
        if (!doc.getUploader().getId().equals(user.getId())) {
            throw new AppException("Access denied", HttpStatus.FORBIDDEN);
        }

        doc.setLatestViewedDateTime(LocalDateTime.now());
        documentRepository.save(doc);
        return documentMapper.toResponse(doc);              // MapStruct
    }

    // ─── VIEW: manager ONLY (department docs) ────────────────

    public List<DocumentResponse> getDepartmentDocuments(String currentUserEmail) {
        User manager = getUserByEmail(currentUserEmail);
        return documentRepository
                .findByDepartmentIdAndIsDeletedFalse(manager.getDepartment().getId())
                .stream()
                .map(documentMapper::toResponse)            // MapStruct method reference
                .collect(Collectors.toList());
    }

    public DocumentResponse getDepartmentDocumentById(String docId, String currentUserEmail) {
        User manager = getUserByEmail(currentUserEmail);
        Document doc = getDocumentOrThrow(docId);

        // RBAC: must be same department
        if (!doc.getDepartment().getId().equals(manager.getDepartment().getId())) {
            throw new AppException("Access denied", HttpStatus.FORBIDDEN);
        }

        doc.setLatestViewedDateTime(LocalDateTime.now());
        documentRepository.save(doc);
        return documentMapper.toResponse(doc);              // MapStruct
    }

    // ─── DELETE: manager ONLY ────────────────────────────────

    public void deleteDocument(String docId, String currentUserEmail) {
        User manager = getUserByEmail(currentUserEmail);
        Document doc = getDocumentOrThrow(docId);

        // RBAC: must be same department
        if (!doc.getDepartment().getId().equals(manager.getDepartment().getId())) {
            throw new AppException("Access denied", HttpStatus.FORBIDDEN);
        }

        doc.setDeleted(true);
        doc.setDeletedAt(LocalDateTime.now());
        documentRepository.save(doc);
    }

    // ─── WEBSOCKET NOTIFICATION ───────────────────────────

    private void sendNotificationTomanager(Document doc, User uploader) {
        Department dept = uploader.getDepartment();
        if (dept == null || dept.getManager() == null) return;

        // Don't notify if uploader IS the manager
        if (dept.getManager().getId().equals(uploader.getId())) return;

        User manager = dept.getManager();
        String content = uploader.getName() + " uploaded a new document: " + doc.getName();

        Notification notification = Notification.builder()
                .triggeredDocument(doc)
                .content(content)
                .receiver(manager)
                .build();

        notificationRepository.save(notification);

        // Push real-time to manager via WebSocket
        messagingTemplate.convertAndSendToUser(
                manager.getEmail(),
                "/queue/notifications",
                Map.of(
                        "id",           notification.getId(),
                        "content",      content,
                        "documentId",   doc.getId(),
                        "documentName", doc.getName()
                )
        );
    }

    // ─── HELPERS ──────────────────────────────────────────

    private User getUserByEmail(String email) {
        return userRepository.findByEmailAndIsDeletedFalse(email)
                .orElseThrow(() -> new AppException("User not found", HttpStatus.NOT_FOUND));
    }

    private Document getDocumentOrThrow(String docId) {
        return documentRepository.findByIdAndIsDeletedFalse(docId)
                .orElseThrow(() -> new AppException("Document not found", HttpStatus.NOT_FOUND));
    }
}