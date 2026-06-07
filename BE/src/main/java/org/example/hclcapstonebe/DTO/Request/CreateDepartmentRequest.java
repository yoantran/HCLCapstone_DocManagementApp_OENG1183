package org.example.hclcapstonebe.DTO.Request;


import jakarta.validation.constraints.*;
import lombok.Data;

@Data
public class CreateDepartmentRequest {
    @NotBlank
    private String name;

    private String managerId;   // Must assign a manager when creating
}