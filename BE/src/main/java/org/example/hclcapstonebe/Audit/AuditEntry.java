package org.example.hclcapstonebe.Audit;


import lombok.Builder;
import lombok.Getter;
import lombok.extern.jackson.Jacksonized;

import java.time.LocalDateTime;

@Getter
@Builder
@Jacksonized
public class AuditEntry {
    private final LocalDateTime timestamp;
    private final String userId;
    private final String name;
    private final String email;
    private final String role;
    private final String method;        // GET, POST, ...
    private final String path;          // /admin/users/123
    private final String action;        // AdminController.createUser
    private final int status;           // 201, 403, ...
    private final long durationMs;
    private final String clientIp;
    private final String error;         // null if success
}