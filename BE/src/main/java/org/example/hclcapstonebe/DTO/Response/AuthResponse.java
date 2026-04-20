package org.example.hclcapstonebe.DTO.Response;


import lombok.*;

@Data @AllArgsConstructor
public class AuthResponse {
    private String token;
    private String role;
    private String email;
    private String name;
}
