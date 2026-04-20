package org.example.hclcapstonebe.DTO.Request;

import lombok.Data;

@Data
public class UpdateProfileRequest {
    private String name;
    private String phoneNumber;
    // avatarImageUrl handled via multipart file upload separately
}