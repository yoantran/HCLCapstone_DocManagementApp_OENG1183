package org.example.hclcapstonebe.DTO.Request;


import lombok.Data;

@Data
public class UpdateDepartmentRequest {
    private String name;
    private String managerId;   // Optional: reassign manager
    private boolean removemanager;   // true = explicitly remove manager
}