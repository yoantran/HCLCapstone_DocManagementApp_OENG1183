package org.example.hclcapstonebe.Controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.ExampleObject;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.example.hclcapstonebe.DTO.Request.UpdateProfileRequest;
import org.example.hclcapstonebe.DTO.Response.UserResponse;
import org.example.hclcapstonebe.Service.UserService;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/users")
@RequiredArgsConstructor
@Tag(name = "Users", description = "Profile management for logged-in users. Available to both STAFF and BOSS.")
@SecurityRequirement(name = "bearerAuth")
public class UserController {

    private final UserService userService;

    @Operation(
            summary = "Get my profile",
            description = "Returns the full profile of the currently authenticated user including department and role info."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "Profile retrieved successfully",
                    content = @Content(
                            mediaType = "application/json",
                            examples = @ExampleObject(value = """
                    {
                        "id": "user-uuid-123",
                        "email": "john.doe@hcl.com",
                        "name": "John Doe",
                        "avatarImageUrl": "avatars/john_avatar.png",
                        "phoneNumber": "0901234567",
                        "departmentId": "dept-uuid-123",
                        "departmentName": "Engineering",
                        "roleEnum": "STAFF",
                        "createdAtDateTime": "2026-04-20T10:00:00"
                    }
                """)
                    )
            ),
            @ApiResponse(responseCode = "401", description = "Unauthorized — JWT missing or expired"),
            @ApiResponse(responseCode = "404", description = "User not found")
    })
    @GetMapping("/me")
    public ResponseEntity<UserResponse> getProfile(
            @AuthenticationPrincipal UserDetails userDetails) {
        return ResponseEntity.ok(userService.getProfile(userDetails.getUsername()));
    }

    @Operation(
            summary = "Update my profile",
            description = """
            Updates the current user's profile. All fields are optional — only send what needs to change.
            Send as multipart/form-data:
            - `data` part: JSON with name and/or phoneNumber
            - `avatar` part: image file (PNG or JPEG)
            """
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "Profile updated successfully",
                    content = @Content(
                            mediaType = "application/json",
                            examples = @ExampleObject(value = """
                    {
                        "id": "user-uuid-123",
                        "email": "john.doe@hcl.com",
                        "name": "John Updated",
                        "avatarImageUrl": "avatars/new_avatar.png",
                        "phoneNumber": "0909999999",
                        "departmentId": "dept-uuid-123",
                        "departmentName": "Engineering",
                        "roleEnum": "STAFF",
                        "createdAtDateTime": "2026-04-20T10:00:00"
                    }
                """)
                    )
            ),
            @ApiResponse(responseCode = "401", description = "Unauthorized"),
            @ApiResponse(responseCode = "404", description = "User not found")
    })
    @PatchMapping(value = "/me", consumes = "multipart/form-data")
    public ResponseEntity<UserResponse> updateProfile(
            @AuthenticationPrincipal UserDetails userDetails,
            @io.swagger.v3.oas.annotations.parameters.RequestBody(
                    description = "Profile update — send as multipart/form-data",
                    content = @Content(
                            examples = @ExampleObject(value = """
                        data: { "name": "John Updated", "phoneNumber": "0909999999" }
                        avatar: [image file]
                    """)
                    )
            )
            @RequestPart(value = "data", required = false) UpdateProfileRequest req,
            @RequestPart(value = "avatar", required = false) MultipartFile avatar) {
        return ResponseEntity.ok(
                userService.updateProfile(userDetails.getUsername(), req, avatar));
    }
}