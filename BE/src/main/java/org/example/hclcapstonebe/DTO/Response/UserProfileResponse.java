package org.example.hclcapstonebe.DTO.Response;


import lombok.Data;
import org.example.hclcapstonebe.Enums.RoleEnum;

import java.time.LocalDateTime;

@Data
public class UserProfileResponse {
    private String id;
    private String email;
    private String name;
    private String avatarSignedUrl;
    private String phoneNumber;
    private String departmentId;
    private String departmentName;
    private RoleEnum roleEnum;
    private LocalDateTime createdAtDateTime;
}
