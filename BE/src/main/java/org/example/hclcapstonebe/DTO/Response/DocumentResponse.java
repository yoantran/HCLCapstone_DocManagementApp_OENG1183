package org.example.hclcapstonebe.DTO.Response;


import lombok.Data;
import java.time.LocalDateTime;

@Data
public class DocumentResponse {
    private String id;
    private String name;
    private String signedUrl; //The FE will use this URL to render/download the file directly from Supabase.
            //It expires after 1 hour (3600 seconds). The FE should re-fetch if expired.
    //FE should not received bucket documentLink
    private String type;
    private String format;
    private Long byteSize;
    private String uploaderId;
    private String uploaderName;
    private String departmentId;
    private LocalDateTime uploadedDateTime;
    private LocalDateTime latestViewedDateTime;
}
