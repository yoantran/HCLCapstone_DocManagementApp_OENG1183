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
@Tag(name = "Documents", description = "Document upload and retrieval. STAFF and BOSS can upload/view own docs. BOSS can also view/delete department docs.")
@SecurityRequirement(name = "bearerAuth")
public class DocumentController {

    private final DocumentService documentService;

    @Operation(
            summary = "Upload a single document",
            description = "Uploads one document file. Automatically assigns it to the uploader's department. Triggers a WebSocket notification to the department boss."
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
                        "documentLink": "uploads/550e8400_Q1_Report.pdf",
                        "type": "CONTRACT",
                        "format": "PDF",
                        "size": 204800,
                        "uploaderId": "user-uuid-123",
                        "uploaderName": "John Doe",
                        "departmentId": "dept-uuid-123",
                        "uploadedDateTime": "2026-04-20T10:30:00",
                        "latestViewedDateTime": null
                    }
                """)
                    )
            ),
            @ApiResponse(responseCode = "400", description = "Invalid file type or document type"),
            @ApiResponse(responseCode = "401", description = "Unauthorized"),
            @ApiResponse(responseCode = "403", description = "Forbidden")
    })
    @PostMapping(value = "/upload", consumes = "multipart/form-data")
    public ResponseEntity<DocumentResponse> uploadOne(
            @Parameter(description = "The document file to upload (PDF, WORD, CSV)")
            @RequestParam("file") MultipartFile file,
            @Parameter(description = "Document type", example = "CONTRACT",
                    schema = @io.swagger.v3.oas.annotations.media.Schema(allowableValues = {"CONTRACT", "BALANCE_SHEET", "PAY_SLIP"}))
            @RequestParam("type") String type,
            @AuthenticationPrincipal UserDetails userDetails) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(documentService.uploadOne(file, type, userDetails.getUsername()));
    }

    @Operation(
            summary = "Upload multiple documents",
            description = "Uploads multiple document files in one request. Each file is processed individually and triggers a boss notification."
    )
    @ApiResponses({
            @ApiResponse(responseCode = "201", description = "All documents uploaded successfully"),
            @ApiResponse(responseCode = "400", description = "Invalid file or type"),
            @ApiResponse(responseCode = "401", description = "Unauthorized")
    })
    @PostMapping(value = "/upload/batch", consumes = "multipart/form-data")
    public ResponseEntity<List<DocumentResponse>> uploadMany(
            @Parameter(description = "List of document files to upload")
            @RequestParam("files") List<MultipartFile> files,
            @Parameter(description = "Document type for all files", example = "PAY_SLIP",
                    schema = @io.swagger.v3.oas.annotations.media.Schema(allowableValues = {"CONTRACT", "BALANCE_SHEET", "PAY_SLIP"}))
            @RequestParam("type") String type,
            @AuthenticationPrincipal UserDetails userDetails) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(documentService.uploadMany(files, type, userDetails.getUsername()));
    }

    @Operation(
            summary = "Get my documents",
            description = "Returns all non-deleted documents uploaded by the currently logged-in user."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "Documents retrieved successfully",
                    content = @Content(
                            mediaType = "application/json",
                            examples = @ExampleObject(value = """
                    [
                        {
                            "id": "doc-uuid-001",
                            "name": "Q1_Report.pdf",
                            "documentLink": "uploads/550e8400_Q1_Report.pdf",
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
    public ResponseEntity<List<DocumentResponse>> getMyDocuments(
            @AuthenticationPrincipal UserDetails userDetails) {
        return ResponseEntity.ok(documentService.getMyDocuments(userDetails.getUsername()));
    }

    @Operation(
            summary = "Get my document by ID",
            description = "Returns a single document uploaded by the current user. Updates latestViewedDateTime on access."
    )
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Document found"),
            @ApiResponse(responseCode = "403", description = "Forbidden — document belongs to another user"),
            @ApiResponse(responseCode = "404", description = "Document not found")
    })
    @GetMapping("/mine/{id}")
    public ResponseEntity<DocumentResponse> getMyDocumentById(
            @Parameter(description = "UUID of the document", example = "doc-uuid-001")
            @PathVariable String id,
            @AuthenticationPrincipal UserDetails userDetails) {
        return ResponseEntity.ok(documentService.getMyDocumentById(id, userDetails.getUsername()));
    }

    @Operation(
            summary = "Get all department documents",
            description = "BOSS ONLY — Returns all non-deleted documents uploaded by any staff in the boss's department."
    )
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Department documents retrieved"),
            @ApiResponse(responseCode = "401", description = "Unauthorized"),
            @ApiResponse(responseCode = "403", description = "Forbidden — BOSS only")
    })
    @GetMapping("/department")
    public ResponseEntity<List<DocumentResponse>> getDepartmentDocuments(
            @AuthenticationPrincipal UserDetails userDetails) {
        return ResponseEntity.ok(documentService.getDepartmentDocuments(userDetails.getUsername()));
    }

    @Operation(
            summary = "Get department document by ID",
            description = "BOSS ONLY — Returns a single document from the boss's department. Updates latestViewedDateTime."
    )
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Document found"),
            @ApiResponse(responseCode = "403", description = "Forbidden — document not in your department"),
            @ApiResponse(responseCode = "404", description = "Document not found")
    })
    @GetMapping("/department/{id}")
    public ResponseEntity<DocumentResponse> getDepartmentDocumentById(
            @Parameter(description = "UUID of the document", example = "doc-uuid-001")
            @PathVariable String id,
            @AuthenticationPrincipal UserDetails userDetails) {
        return ResponseEntity.ok(documentService.getDepartmentDocumentById(id, userDetails.getUsername()));
    }

    @Operation(
            summary = "Delete a document",
            description = "BOSS ONLY — Soft deletes a document in the boss's department. Sets isDeleted=true, document is NOT permanently removed."
    )
    @ApiResponses({
            @ApiResponse(responseCode = "204", description = "Document deleted successfully"),
            @ApiResponse(responseCode = "403", description = "Forbidden — document not in your department or not a BOSS"),
            @ApiResponse(responseCode = "404", description = "Document not found")
    })
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteDocument(
            @Parameter(description = "UUID of the document to delete", example = "doc-uuid-001")
            @PathVariable String id,
            @AuthenticationPrincipal UserDetails userDetails) {
        documentService.deleteDocument(id, userDetails.getUsername());
        return ResponseEntity.noContent().build();
    }
}