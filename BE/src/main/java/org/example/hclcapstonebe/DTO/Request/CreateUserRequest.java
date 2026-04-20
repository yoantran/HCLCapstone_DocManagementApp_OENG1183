package org.example.hclcapstonebe.DTO.Request;


import jakarta.validation.constraints.*;
import lombok.Data;
import org.example.hclcapstonebe.Enums.RoleEnum;

@Data
public class CreateUserRequest {
    @NotBlank @Email
    private String email;
    @NotBlank
    private String password;
    @NotBlank
    private String name;
    private String phoneNumber;
    @NotNull
    private RoleEnum roleEnum;
    @NotBlank
    private String departmentId;
}