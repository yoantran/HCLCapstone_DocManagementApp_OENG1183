package org.example.hclcapstonebe.DTO.Request;


import lombok.Data;

@Data
public class UpdateDepartmentRequest {
    private String name;
    private String bossId;   // Optional: reassign boss
    private boolean removeBoss;   // true = explicitly remove boss
}