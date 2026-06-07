package org.example.hclcapstonebe.DTO.Response;


import lombok.Data;
import java.time.LocalDateTime;
import java.util.UUID;

@Data
public class NotificationResponse {
    private String id;
    private String content;
    private String triggeredDocumentId;
    private String triggeredDocumentName;
    private boolean hasRead ;
    private LocalDateTime isReadDateTime;
    private LocalDateTime createdAt;
}
