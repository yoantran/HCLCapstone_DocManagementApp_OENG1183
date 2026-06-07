package org.example.hclcapstonebe.Controller;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.ExampleObject;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.example.hclcapstonebe.DTO.Request.UpdateProfileRequest;
import org.example.hclcapstonebe.DTO.Response.UserProfileResponse;
import org.example.hclcapstonebe.Service.UserService;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/users")
@RequiredArgsConstructor
@Tag(name = "Users", description = "Profile management for logged-in users. Available to both STAFF and manager.")
@SecurityRequirement(name = "bearerAuth")
public class UserController {

    private final UserService userService;

    // ─── GET MY PROFILE ───────────────────────────────────────────────────────

    @Operation(
            summary = "Get my profile",
            description = """
                    Returns the currently logged-in user's profile.
                    Includes a signed URL for the avatar image (valid for 1 hour).
                    Available to both Staff and Boss.
                    """
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
                        "name": "John Doe",
                        "email": "john.doe@example.com",
                        "phoneNumber": "0901234567",
                        "role": "STAFF",
                        "departmentId": "dept-uuid-123",
                        "departmentName": "Finance",
                        "avatarSignedUrl": "https://pkbwoortbtsvbcggybia.supabase.co/storage/v1/object/sign/images/uuid_avatar.png?token=eyJ..."
                    }
                    """)
                    )
            ),
            @ApiResponse(responseCode = "401", description = "Unauthorized — JWT token missing or expired"),
            @ApiResponse(responseCode = "404", description = "User not found")
    })
    @GetMapping("/me")
    public ResponseEntity<UserProfileResponse> getMyProfile(
            @AuthenticationPrincipal UserDetails userDetails) {
        return ResponseEntity.ok(userService.getProfile(userDetails.getUsername()));
    }

    // ─── UPDATE MY PROFILE ────────────────────────────────────────────────────

    @Operation(
            summary = "Update my profile",
            description = """
                    Updates the currently logged-in user's name, phone number, and/or avatar image.
                    All fields are optional — only provided fields will be updated.
                    
                    Avatar rules:
                    - Allowed formats: JPEG, PNG
                    - Max file size: 10MB
                    - Old avatar is automatically deleted from storage when a new one is uploaded
                    - A signed URL (valid for 1 hour) is returned to view the new avatar
                    
                    Available to both Staff and Boss.
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
                        "name": "John Updated",
                        "email": "john.doe@example.com",
                        "phoneNumber": "0909999999",
                        "role": "STAFF",
                        "departmentId": "dept-uuid-123",
                        "departmentName": "Finance",
                        "avatarSignedUrl": "https://pkbwoortbtsvbcggybia.supabase.co/storage/v1/object/sign/images/uuid_new_avatar.png?token=eyJ..."
                    }
                    """)
                    )
            ),
            @ApiResponse(responseCode = "400", description = "Invalid avatar format (only JPEG, PNG allowed) or file exceeds 10MB"),
            @ApiResponse(responseCode = "401", description = "Unauthorized — JWT token missing or expired"),
            @ApiResponse(responseCode = "404", description = "User not found")
    })
    @PutMapping(value = "/me", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<UserProfileResponse> updateMyProfile(
            @Parameter(description = "Updated name (optional)")
            @RequestParam(value = "name", required = false) String name,

            @Parameter(description = "Updated phone number (optional)")
            @RequestParam(value = "phoneNumber", required = false) String phoneNumber,

            @Parameter(description = "New avatar image — JPEG or PNG, max 10MB (optional). Replaces and deletes the old avatar.")
            @RequestParam(value = "avatar", required = false) MultipartFile avatar,

            @AuthenticationPrincipal UserDetails userDetails) {

        UpdateProfileRequest request = new UpdateProfileRequest();
        request.setName(name);
        request.setPhoneNumber(phoneNumber);

        return ResponseEntity.ok(
                userService.updateProfile(userDetails.getUsername(), request, avatar)
        );
    }
}