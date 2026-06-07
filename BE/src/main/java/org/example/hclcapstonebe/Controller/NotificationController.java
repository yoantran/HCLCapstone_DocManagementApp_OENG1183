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
import org.example.hclcapstonebe.DTO.Response.NotificationResponse;
import org.example.hclcapstonebe.Service.NotificationService;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/notifications")
@RequiredArgsConstructor
@Tag(name = "Notifications", description = "manager ONLY — Real-time and historical notifications triggered when staff upload documents.")
@SecurityRequirement(name = "bearerAuth")
public class NotificationController {

    private final NotificationService notificationService;

    @Operation(
            summary = "Get all my notifications",
            description = "manager ONLY — Returns all notifications received by the current manager, ordered by newest first."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "Notifications retrieved successfully",
                    content = @Content(
                            mediaType = "application/json",
                            examples = @ExampleObject(value = """
                    [
                        {
                            "id": "notif-uuid-001",
                            "content": "John Doe uploaded a new document: Q1_Report.pdf",
                            "triggeredDocumentId": "doc-uuid-001",
                            "triggeredDocumentName": "Q1_Report.pdf",
                            "read": false,
                            "isReadDateTime": null,
                            "createdAt": "2026-04-20T10:30:00"
                        },
                        {
                            "id": "notif-uuid-002",
                            "content": "Jane Smith uploaded a new document: PaySlip_March.pdf",
                            "triggeredDocumentId": "doc-uuid-002",
                            "triggeredDocumentName": "PaySlip_March.pdf",
                            "read": true,
                            "isReadDateTime": "2026-04-20T11:00:00",
                            "createdAt": "2026-04-19T09:00:00"
                        }
                    ]
                """)
                    )
            ),
            @ApiResponse(responseCode = "401", description = "Unauthorized"),
            @ApiResponse(responseCode = "403", description = "Forbidden — manager only")
    })
    @GetMapping
    public ResponseEntity<List<NotificationResponse>> getMyNotifications(
            @AuthenticationPrincipal UserDetails userDetails) {
        return ResponseEntity.ok(notificationService.getMyNotifications(userDetails.getUsername()));
    }

    @Operation(
            summary = "Mark notification as read",
            description = "manager ONLY — Marks a specific notification as read and records the timestamp."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "Notification marked as read",
                    content = @Content(
                            mediaType = "application/json",
                            examples = @ExampleObject(value = """
                    {
                        "id": "notif-uuid-001",
                        "content": "John Doe uploaded a new document: Q1_Report.pdf",
                        "triggeredDocumentId": "doc-uuid-001",
                        "triggeredDocumentName": "Q1_Report.pdf",
                        "read": true,
                        "isReadDateTime": "2026-04-20T12:00:00",
                        "createdAt": "2026-04-20T10:30:00"
                    }
                """)
                    )
            ),
            @ApiResponse(responseCode = "403", description = "Forbidden — notification belongs to another user"),
            @ApiResponse(responseCode = "404", description = "Notification not found")
    })
    @PatchMapping("/{id}/read")
    public ResponseEntity<NotificationResponse> markAsRead(
            @Parameter(description = "UUID of the notification to mark as read", example = "notif-uuid-001")
            @PathVariable String id,
            @AuthenticationPrincipal UserDetails userDetails) {
        return ResponseEntity.ok(notificationService.markAsRead(id, userDetails.getUsername()));
    }
}