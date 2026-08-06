package org.example.hclcapstonebe.DTO.Response;


import lombok.AllArgsConstructor;
import lombok.Getter;

import java.time.LocalDateTime;

@Getter
@AllArgsConstructor
public class AuditLogResponse {
    private LocalDateTime timestamp;
    private String userId;
    private String name;
    private String email;
    private String role;
    private String method;
    private String path;
    private String action;
    private int status;
    private long durationMs;
    private String clientIp;
    private String error;
}