package org.example.hclcapstonebe.DTO.Request;


import jakarta.validation.constraints.*;
import lombok.Data;

@Data
public class CreateDepartmentRequest {
    @NotBlank
    private String name;
    @NotBlank
    private String bossId;   // Must assign a boss when creating
}