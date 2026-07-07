package org.example.hclcapstonebe.DTO.Response;


import lombok.*;

import java.util.UUID;

@Data @AllArgsConstructor
public class AuthResponse {
    private String id;
    private String token;
    private String role;
    private String email;
    private String name;
    private String departmentId;
}
