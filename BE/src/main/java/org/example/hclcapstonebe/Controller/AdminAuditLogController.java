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
import org.example.hclcapstonebe.Audit.AuditLogStore;
import org.example.hclcapstonebe.DTO.Response.AuditLogResponse;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/admin/audit-logs")
@RequiredArgsConstructor
@Tag(name = "Admin - Audit Logs", description = "In-memory audit trail of API calls. ADMIN only.")
@SecurityRequirement(name = "bearerAuth")
public class AdminAuditLogController {

    private final AuditLogStore store;

    @Operation(
            summary = "Query the audit trail",
            description = """
        Returns recent API calls, newest first. All filters are optional and combine with AND.

        **Important:** Entries live in memory only (max 1000). They are lost on restart
        and are not shared across instances if you run more than one.
        """
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "Entries returned",
                    content = @Content(
                            mediaType = "application/json",
                            examples = @ExampleObject(value = """
                    [
                        {
                            "timestamp": "2026-07-22T14:03:11.482",
                            "userId": "550e8400-e29b-41d4-a716-446655440000",
                            "email": "admin@hcl.com",
                            "role": "ROLE_ADMIN",
                            "method": "DELETE",
                            "path": "/admin/users/660e9500-f30c-52e5-b827-557766551111",
                            "action": "AdminController.deleteUser",
                            "status": 204,
                            "durationMs": 34,
                            "clientIp": "203.0.113.42",
                            "error": null
                        }
                    ]
                """)
                    )
            ),
            @ApiResponse(responseCode = "401", description = "Unauthorized"),
            @ApiResponse(responseCode = "403", description = "Forbidden — ADMIN only")
    })
    @GetMapping
    public ResponseEntity<List<AuditLogResponse>> getLogs(
            @Parameter(description = "Filter by user UUID") @RequestParam(required = false) String userId,
            @Parameter(description = "Filter by HTTP method", example = "DELETE") @RequestParam(required = false) String method,
            @Parameter(description = "Substring match on path", example = "/admin/users") @RequestParam(required = false) String path,
            @Parameter(description = "ISO date", example = "2026-07-22")
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date,
            @RequestParam(defaultValue = "100") int limit) {

        List<AuditLogResponse> body = store.query(userId, method, path, date, Math.min(limit, 1000))
                .stream()
                .map(e -> new AuditLogResponse(
                        e.getTimestamp(), e.getUserId(), e.getName(), e.getEmail(), e.getRole(),
                        e.getMethod(), e.getPath(), e.getAction(), e.getStatus(),
                        e.getDurationMs(), e.getClientIp(), e.getError()))
                .toList();

        return ResponseEntity.ok(body);
    }

    @Operation(summary = "Buffer stats", description = "How many entries are currently held.")
    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> stats() {
        return ResponseEntity.ok(Map.of("entries", store.size(), "capacity", 1000));
    }

    @Operation(summary = "Clear the buffer")
    @ApiResponses(@ApiResponse(responseCode = "204", description = "Cleared"))
    @DeleteMapping
    public ResponseEntity<Void> clear() {
        store.clear();
        return ResponseEntity.noContent().build();
    }
}