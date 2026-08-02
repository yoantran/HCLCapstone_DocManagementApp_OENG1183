package org.example.hclcapstonebe.Controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.ExampleObject;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.example.hclcapstonebe.Audit.AuditAction;
import org.example.hclcapstonebe.DTO.Request.LoginRequest;
import org.example.hclcapstonebe.DTO.Response.AuthResponse;
import org.example.hclcapstonebe.Service.AuthService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/auth")
@RequiredArgsConstructor
@Tag(name = "Auth", description = "Authentication APIs — login and logout. No token required.")
public class AuthController {

    private final AuthService authService;

    @Operation(
            summary = "Login",
            description = "Authenticates a user with email and password. Returns a JWT token to use in all subsequent requests via the Authorization header."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "Login successful — JWT token returned",
                    content = @Content(
                            mediaType = "application/json",
                            examples = @ExampleObject(value = """
                    {                        "id": "bac1234",
                        "token": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJqb2huQGhjbC5jb20iLCJpYXQiOjE3MTM1OTAwMDAsImV4cCI6MTcxMzY3NjQwMH0.abc123",
                        "roleEnum": "STAFF",
                        "email": "john.doe@hcl.com",
                        "name": "John Doe"
                    }
                """)
                    )
            ),
            @ApiResponse(responseCode = "401", description = "Invalid email or password")
    })
    @PostMapping("/login")
    @AuditAction("Logged in")
    public ResponseEntity<AuthResponse> login(
            @io.swagger.v3.oas.annotations.parameters.RequestBody(
                    description = "Login credentials",
                    required = true,
                    content = @Content(
                            examples = @ExampleObject(value = """
                        {
                            "email": "admin@hcl.com",
                            "password": "password123"
                        }
                    """)
                    )
            )
            @Valid @RequestBody LoginRequest request) {
        return ResponseEntity.ok(authService.login(request));
    }

    @Operation(
            summary = "Logout",
            description = "Logs out the current user. Since JWT is stateless, the client must discard the token. Server-side blacklisting can be added later."
    )
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Logged out successfully"),
            @ApiResponse(responseCode = "401", description = "Unauthorized — token missing or invalid")
    })
    @PostMapping("/logout")
    @AuditAction("Logged out")
    public ResponseEntity<String> logout() {
        authService.logout();
        return ResponseEntity.ok("Logged out successfully");
    }
}