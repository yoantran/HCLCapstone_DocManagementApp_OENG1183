package org.example.hclcapstonebe.DTO.Response;


import lombok.Data;
import org.example.hclcapstonebe.Enums.ScanStatus;

import java.time.LocalDateTime;
import java.util.UUID;

@Data
public class DocumentResponse {
    private String id;
    private String name;
    private ScanStatus scanStatus;
    private String scanMessage;
    private LocalDateTime scannedAt;
    private boolean isAccessible;
    private String signedUrl;
    private String type;
    private String format;
    private Long byteSize;
    private String uploaderId;
    private String uploaderName;
    private String departmentId;
    private String departmentName;
    private LocalDateTime uploadedDateTime;
    private LocalDateTime latestViewedDateTime;
}
