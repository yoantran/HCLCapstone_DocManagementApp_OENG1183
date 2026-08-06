package org.example.hclcapstonebe.Controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.ExampleObject;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.example.hclcapstonebe.Audit.AuditAction;
import org.example.hclcapstonebe.DTO.Response.DocumentResponse;
import org.example.hclcapstonebe.Service.DocumentService;
import org.springframework.http.*;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import java.util.List;

@RestController
@RequestMapping("/documents")
@RequiredArgsConstructor
@Tag(name = "Documents", description = "Document upload and retrieval. STAFF and manager can upload/view own docs. manager can also view/delete department docs.")
@SecurityRequirement(name = "bearerAuth")
public class DocumentController {

    private final DocumentService documentService;

    @Operation(
            summary = "Upload a single document",
            description = """
                Uploads one document file to the Supabase documents bucket.
                Automatically assigns it to the uploader's department.
                Triggers a WebSocket notification to the department manager.
                A signed URL (valid for 1 hour) is returned to view the document.
                
                Security & Validation Pipeline:
                - Allowed formats: PDF, DOCX, CSV, PNG, JPEG, JPG (Max file size: 10MB)
                - Binary Magic Bytes Header Validation: Verifies %PDF for PDF and PK.. for DOCX
                - ClamAV Virus/Malware Scanning: Scans the uploaded file stream prior to storage
                - Automatic Filename Deduplication: Renames duplicates (e.g., file (1).pdf) per user
                """
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "201",
                    description = "Document uploaded successfully",
                    content = @Content(
                            mediaType = "application/json",
                            examples = @ExampleObject(value = """
                {
                    "id": "doc-uuid-001",
                    "name": "Q1_Report.pdf",
                    "type": "CONTRACT",
                    "format": "PDF",
                    "size": 204800,
                    "uploaderId": "user-uuid-123",
                    "uploaderName": "John Doe",
                    "departmentId": "dept-uuid-123",
                    "uploadedDateTime": "2026-04-20T10:30:00",
                    "latestViewedDateTime": null,
                    "signedUrl": "https://pkbwoortbtsvbcggybia.supabase.co/storage/v1/object/sign/documents/uuid_Q1_Report.pdf?token=eyJ..."
                }
            """)
                    )
            ),
            @ApiResponse(responseCode = "400", description = "Invalid file format/extension, invalid document type, file exceeds 10MB, or invalid structural file signature match detected (magic bytes mismatch)"),
            @ApiResponse(responseCode = "401", description = "Unauthorized — JWT token missing or expired"),
            @ApiResponse(responseCode = "403", description = "Forbidden — insufficient permissions"),
            @ApiResponse(responseCode = "422", description = "Unprocessable Entity — Malware virus variant threat vector flagged within upload stream by ClamAV scanner")
    })
    @PostMapping(value = "/upload", consumes = "multipart/form-data")
    @AuditAction("Uploaded document '{file}'")
    public ResponseEntity<DocumentResponse> uploadOne(
            @Parameter(description = "The document file to upload. Allowed formats: PDF, DOCX, CSV, PNG, JPG, JPEG. Max size: 10MB")
            @RequestParam("file") MultipartFile file,
            @Parameter(
                    description = "Document type",
                    example = "CONTRACT",
                    schema = @io.swagger.v3.oas.annotations.media.Schema(
                            allowableValues = {"CONTRACT", "BALANCE_SHEET", "PAY_SLIP"}
                    )
            )
            @RequestParam("type") String type,
            @AuthenticationPrincipal UserDetails userDetails) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(documentService.uploadOne(file, type, userDetails.getUsername()));
    }

    @Operation(
            summary = "Upload multiple documents",
            description = """
                Uploads multiple document files in one request.
                Each file is processed individually and triggers a manager notification.
                All files in the batch must share the same document type.
                A signed URL (valid for 1 hour) is returned per document.
                
                Security & Validation Pipeline (per file):
                - Allowed formats: PDF, DOCX, CSV, PNG, JPG, JPEG (Max file size per file: 10MB, Max batch limit: 10 files)
                - Binary Magic Bytes Header Validation: Verifies %PDF for PDF and PK.. for DOCX
                - ClamAV Virus/Malware Scanning: Scans each uploaded file stream prior to storage
                - Automatic Filename Deduplication: Renames duplicates (e.g., file (1).pdf) per user
                """
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "201",
                    description = "All documents uploaded successfully",
                    content = @Content(
                            mediaType = "application/json",
                            examples = @ExampleObject(value = """
                [
                    {
                        "id": "doc-uuid-001",
                        "name": "Q1_Report.pdf",
                        "type": "PAY_SLIP",
                        "format": "PDF",
                        "size": 204800,
                        "uploaderId": "user-uuid-123",
                        "uploaderName": "John Doe",
                        "departmentId": "dept-uuid-123",
                        "uploadedDateTime": "2026-04-20T10:30:00",
                        "latestViewedDateTime": null,
                        "signedUrl": "https://pkbwoortbtsvbcggybia.supabase.co/storage/v1/object/sign/documents/uuid_Q1_Report.pdf?token=eyJ..."
                    }
                ]
            """)
                    )
            ),
            @ApiResponse(responseCode = "400", description = "Invalid file format/extension, invalid document type, file exceeds 10MB, batch exceeds 10 files, or invalid structural file signature match detected (magic bytes mismatch)"),
            @ApiResponse(responseCode = "401", description = "Unauthorized — JWT token missing or expired"),
            @ApiResponse(responseCode = "403", description = "Forbidden — insufficient permissions"),
            @ApiResponse(responseCode = "422", description = "Unprocessable Entity — Malware virus variant threat vector flagged within upload stream by ClamAV scanner")
    })
    @PostMapping(value = "/upload/batch", consumes = "multipart/form-data")
    @AuditAction("Uploaded multiple documents")
    public ResponseEntity<List<DocumentResponse>> uploadMany(
            @Parameter(description = "List of document files to upload. Allowed formats: PDF, DOCX, CSV, PNG, JPG, JPEG. Max size per file: 10MB")
            @RequestParam("files") List<MultipartFile> files,
            @Parameter(
                    description = "Document type applied to all files in the batch",
                    example = "PAY_SLIP",
                    schema = @io.swagger.v3.oas.annotations.media.Schema(
                            allowableValues = {"CONTRACT", "BALANCE_SHEET", "PAY_SLIP"}
                    )
            )
            @RequestParam("type") String type,
            @AuthenticationPrincipal UserDetails userDetails) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(documentService.uploadMany(files, type, userDetails.getUsername()));
    }
    @Operation(
            summary = "Staff only: Get my uploaded documents",
            description = "Returns all non-deleted documents uploaded by the currently logged-in user."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "Documents retrieved successfully,                     \"Signed url is available for 1 hour to view document\"\n"
                    ,
                    content = @Content(
                            mediaType = "application/json",
                            examples = @ExampleObject(value = """
                    [
                        {
                            "id": "doc-uuid-001",
                            "name": "Q1_Report.pdf",
                            "signedUrl": "uploads/550e8400_Q1_Report.pdf",
                            "type": "CONTRACT",
                            "format": "PDF",
                            "size": 204800,
                            "uploaderId": "user-uuid-123",
                            "uploaderName": "John Doe",
                            "departmentId": "dept-uuid-123",
                            "uploadedDateTime": "2026-04-20T10:30:00",
                            "latestViewedDateTime": "2026-04-20T11:00:00"
                        }
                    ]
                """)
                    )
            ),
            @ApiResponse(responseCode = "401", description = "Unauthorized")
    })
    @GetMapping("/mine")
    @AuditAction("Viewed own documents")
    public ResponseEntity<List<DocumentResponse>> getMyDocuments(
            @AuthenticationPrincipal UserDetails userDetails) {
        return ResponseEntity.ok(documentService.getMyDocuments(userDetails.getUsername()));
    }

    @Operation(
            summary = "Staff only: Get my uploaded document by ID",
            description = "Returns a single document uploaded by the current user. Updates latestViewedDateTime on access."
    )
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Document found"),
            @ApiResponse(responseCode = "403", description = "Forbidden — document belongs to another user"),
            @ApiResponse(responseCode = "404", description = "Document not found")
    })
    @GetMapping("/mine/{id}")
    @AuditAction("Viewed document '{documentId}'")
    public ResponseEntity<DocumentResponse> getMyDocumentById(
            @Parameter(description = "UUID of the document", example = "doc-uuid-001")
            @PathVariable("id") String documentId,
            @AuthenticationPrincipal UserDetails userDetails) {
        return ResponseEntity.ok(documentService.getMyDocumentById(documentId, userDetails.getUsername()));
    }

    @Operation(
            summary = "Get all department documents",
            description = "manager ONLY — Returns all non-deleted documents uploaded by any staff in the manager's department."
    )
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Department documents retrieved"),
            @ApiResponse(responseCode = "401", description = "Unauthorized"),
            @ApiResponse(responseCode = "403", description = "Forbidden — manager only")
    })
    @GetMapping("/department")
    @AuditAction("Viewed department documents")
    public ResponseEntity<List<DocumentResponse>> getDepartmentDocuments(
            @AuthenticationPrincipal UserDetails userDetails) {
        return ResponseEntity.ok(documentService.getDepartmentDocuments(userDetails.getUsername()));
    }

    @Operation(
            summary = "Get department document by ID",
            description = "manager ONLY — Returns a single document from the manager's department. Updates latestViewedDateTime."
    )
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Document found"),
            @ApiResponse(responseCode = "403", description = "Forbidden — document not in your department"),
            @ApiResponse(responseCode = "404", description = "Document not found")
    })
    @GetMapping("/department/{id}")
    @AuditAction("Viewed document '{documentId}'")
    public ResponseEntity<DocumentResponse> getDepartmentDocumentById(
            @Parameter(description = "UUID of the document", example = "doc-uuid-001")
            @PathVariable("id") String documentId,
            @AuthenticationPrincipal UserDetails userDetails) {
        return ResponseEntity.ok(documentService.getDepartmentDocumentById(documentId, userDetails.getUsername()));
    }

    @Operation(
            summary = "Delete a document",
            description = "manager ONLY — Soft deletes a document in the manager's department. Sets isDeleted=true, document is NOT permanently removed."
    )
    @ApiResponses({
            @ApiResponse(responseCode = "204", description = "Document deleted successfully"),
            @ApiResponse(responseCode = "403", description = "Forbidden — document not in your department or not a manager"),
            @ApiResponse(responseCode = "404", description = "Document not found")
    })
    @DeleteMapping("/{id}")
    @AuditAction("Deleted document '{documentId}'")
    public ResponseEntity<Void> deleteDocument(
            @Parameter(description = "UUID of the document to delete", example = "doc-uuid-001")
            @PathVariable("id") String documentId,
            @AuthenticationPrincipal UserDetails userDetails) {
        documentService.deleteDocument(documentId, userDetails.getUsername());
        return ResponseEntity.noContent().build();
    }
}