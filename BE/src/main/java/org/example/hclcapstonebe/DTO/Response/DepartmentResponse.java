package org.example.hclcapstonebe.DTO.Response;


import lombok.Data;
import java.time.LocalDateTime;

@Data
public class DepartmentResponse {
    private String id;
    private String name;
    private String bossId;
    private String bossName;
    private LocalDateTime createdAtDateTime;
}