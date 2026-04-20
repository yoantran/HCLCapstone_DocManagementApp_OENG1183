package org.example.hclcapstonebe.DTO.Response;


import lombok.Data;
import java.time.LocalDateTime;

@Data
public class DocumentResponse {
    private String id;
    private String name;
    private String documentLink;
    private String type;
    private String format;
    private Long size;
    private String uploaderId;
    private String uploaderName;
    private String departmentId;
    private LocalDateTime uploadedDateTime;
    private LocalDateTime latestViewedDateTime;
}
