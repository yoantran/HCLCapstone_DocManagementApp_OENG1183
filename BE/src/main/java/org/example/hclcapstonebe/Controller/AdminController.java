package org.example.hclcapstonebe.Controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.ExampleObject;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.example.hclcapstonebe.DTO.Request.CreateDepartmentRequest;
import org.example.hclcapstonebe.DTO.Request.CreateUserRequest;
import org.example.hclcapstonebe.DTO.Request.UpdateDepartmentRequest;
import org.example.hclcapstonebe.DTO.Response.DepartmentResponse;
import org.example.hclcapstonebe.DTO.Response.UserResponse;
import org.example.hclcapstonebe.Service.AdminService;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/admin")
@RequiredArgsConstructor
@Tag(name = "Admin", description = "Admin-only APIs for managing users and departments. Requires ADMIN role.")
@SecurityRequirement(name = "bearerAuth")
public class AdminController {

    private final AdminService adminService;

    // ─── USERS ────────────────────────────────────────────

    @Operation(
            summary = "Create a new user",
            description = "Creates a new user (STAFF or BOSS) and assigns them to a department. Only ADMIN can perform this action."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "201",
                    description = "User created successfully",
                    content = @Content(
                            mediaType = "application/json",
                            schema = @Schema(implementation = UserResponse.class),
                            examples = @ExampleObject(value = """
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "email": "john.doe@hcl.com",
                        "name": "John Doe",
                        "avatarImageUrl": null,
                        "phoneNumber": "0901234567",
                        "departmentId": "dept-uuid-123",
                        "departmentName": "Engineering",
                        "roleEnum": "STAFF",
                        "createdAtDateTime": "2026-04-20T10:00:00"
                    }
                """)
                    )
            ),
            @ApiResponse(responseCode = "400", description = "Invalid request body or missing required fields"),
            @ApiResponse(responseCode = "401", description = "Unauthorized — JWT token missing or invalid"),
            @ApiResponse(responseCode = "403", description = "Forbidden — Only ADMIN can access this endpoint"),
            @ApiResponse(responseCode = "404", description = "Department not found"),
            @ApiResponse(responseCode = "409", description = "Email already in use")
    })
    @PostMapping("/users")
    public ResponseEntity<UserResponse> createUser(
            @io.swagger.v3.oas.annotations.parameters.RequestBody(
                    description = "User creation payload",
                    required = true,
                    content = @Content(
                            examples = @ExampleObject(value = """
                        {
                            "email": "john.doe@hcl.com",
                            "password": "securePassword123",
                            "name": "John Doe",
                            "phoneNumber": "0901234567",
                            "roleEnum": "STAFF",
                            "departmentId": "dept-uuid-123"
                        }
                    """)
                    )
            )
            @Valid @RequestBody CreateUserRequest req) {
        return ResponseEntity.status(HttpStatus.CREATED).body(adminService.createUser(req));
    }

    @Operation(
            summary = "Soft delete a user",
            description = """
            Soft deletes a user by setting isDeleted=true. The user record is NOT permanently removed.
            ⚠️ If the user is a BOSS, you must reassign a new boss to their department first,
            otherwise this will return 400.
            """
    )
    @ApiResponses({
            @ApiResponse(responseCode = "204", description = "User deleted successfully"),
            @ApiResponse(responseCode = "400", description = "Cannot delete a BOSS without reassigning department boss first"),
            @ApiResponse(responseCode = "401", description = "Unauthorized"),
            @ApiResponse(responseCode = "403", description = "Forbidden — ADMIN only"),
            @ApiResponse(responseCode = "404", description = "User not found")
    })
    @DeleteMapping("/users/{id}")
    public ResponseEntity<Void> deleteUser(
            @Parameter(description = "UUID of the user to delete", example = "550e8400-e29b-41d4-a716-446655440000")
            @PathVariable String id) {
        adminService.deleteUser(id);
        return ResponseEntity.noContent().build();
    }

    @Operation(
            summary = "Get all users",
            description = "Returns a list of all non-deleted users in the system."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "List of users returned successfully",
                    content = @Content(
                            mediaType = "application/json",
                            examples = @ExampleObject(value = """
                    [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "email": "john.doe@hcl.com",
                            "name": "John Doe",
                            "avatarImageUrl": null,
                            "phoneNumber": "0901234567",
                            "departmentId": "dept-uuid-123",
                            "departmentName": "Engineering",
                            "roleEnum": "STAFF",
                            "createdAtDateTime": "2026-04-20T10:00:00"
                        },
                        {
                            "id": "660e9500-f30c-52e5-b827-557766551111",
                            "email": "jane.smith@hcl.com",
                            "name": "Jane Smith",
                            "avatarImageUrl": "avatars/jane.png",
                            "phoneNumber": "0907654321",
                            "departmentId": "dept-uuid-123",
                            "departmentName": "Engineering",
                            "roleEnum": "BOSS",
                            "createdAtDateTime": "2026-04-19T09:00:00"
                        }
                    ]
                """)
                    )
            ),
            @ApiResponse(responseCode = "401", description = "Unauthorized"),
            @ApiResponse(responseCode = "403", description = "Forbidden — ADMIN only")
    })
    @GetMapping("/users")
    public ResponseEntity<List<UserResponse>> getAllUsers() {
        return ResponseEntity.ok(adminService.getAllUsers());
    }

    @Operation(
            summary = "Get user by ID",
            description = "Returns a single user by their UUID."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "User found",
                    content = @Content(
                            mediaType = "application/json",
                            examples = @ExampleObject(value = """
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "email": "john.doe@hcl.com",
                        "name": "John Doe",
                        "avatarImageUrl": null,
                        "phoneNumber": "0901234567",
                        "departmentId": "dept-uuid-123",
                        "departmentName": "Engineering",
                        "roleEnum": "STAFF",
                        "createdAtDateTime": "2026-04-20T10:00:00"
                    }
                """)
                    )
            ),
            @ApiResponse(responseCode = "401", description = "Unauthorized"),
            @ApiResponse(responseCode = "403", description = "Forbidden — ADMIN only"),
            @ApiResponse(responseCode = "404", description = "User not found")
    })
    @GetMapping("/users/{id}")
    public ResponseEntity<UserResponse> getUserById(
            @Parameter(description = "UUID of the user", example = "550e8400-e29b-41d4-a716-446655440000")
            @PathVariable String id) {
        return ResponseEntity.ok(adminService.getUserById(id));
    }

    // ─── DEPARTMENTS ──────────────────────────────────────

    @Operation(
            summary = "Create a new department",
            description = "Creates a new department. A BOSS user must be assigned at creation time — departments cannot exist without a boss."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "201",
                    description = "Department created successfully",
                    content = @Content(
                            mediaType = "application/json",
                            examples = @ExampleObject(value = """
                    {
                        "id": "dept-uuid-123",
                        "name": "Engineering",
                        "bossId": "660e9500-f30c-52e5-b827-557766551111",
                        "bossName": "Jane Smith",
                        "createdAtDateTime": "2026-04-20T09:00:00"
                    }
                """)
                    )
            ),
            @ApiResponse(responseCode = "400", description = "Assigned user is not a BOSS role"),
            @ApiResponse(responseCode = "401", description = "Unauthorized"),
            @ApiResponse(responseCode = "403", description = "Forbidden — ADMIN only"),
            @ApiResponse(responseCode = "404", description = "Boss user not found")
    })
    @PostMapping("/departments")
    public ResponseEntity<DepartmentResponse> createDepartment(
            @io.swagger.v3.oas.annotations.parameters.RequestBody(
                    description = "Department creation payload. bossId must be an existing user with BOSS role.",
                    required = true,
                    content = @Content(
                            examples = @ExampleObject(value = """
                        {
                            "name": "Engineering",
                            "bossId": "660e9500-f30c-52e5-b827-557766551111"
                        }
                    """)
                    )
            )
            @Valid @RequestBody CreateDepartmentRequest req) {
        return ResponseEntity.status(HttpStatus.CREATED).body(adminService.createDepartment(req));
    }

    @Operation(
            summary = "Update a department",
            description = """
            Updates a department's name and/or reassigns its boss.
            ⚠️ When reassigning boss: the new boss must already belong to this department.
            All fields are optional — only send what you want to change.
            """
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "Department updated successfully",
                    content = @Content(
                            mediaType = "application/json",
                            examples = @ExampleObject(value = """
                    {
                        "id": "dept-uuid-123",
                        "name": "Engineering Updated",
                        "bossId": "770f0600-g41d-63f6-c938-668877662222",
                        "bossName": "Bob Johnson",
                        "createdAtDateTime": "2026-04-20T09:00:00"
                    }
                """)
                    )
            ),
            @ApiResponse(responseCode = "400", description = "New boss does not belong to this department or is not BOSS role"),
            @ApiResponse(responseCode = "401", description = "Unauthorized"),
            @ApiResponse(responseCode = "403", description = "Forbidden — ADMIN only"),
            @ApiResponse(responseCode = "404", description = "Department or new boss not found")
    })
    @PutMapping("/departments/{id}")
    public ResponseEntity<DepartmentResponse> updateDepartment(
            @Parameter(description = "UUID of the department to update", example = "dept-uuid-123")
            @PathVariable String id,
            @io.swagger.v3.oas.annotations.parameters.RequestBody(
                    description = "Fields to update. Both are optional.",
                    content = @Content(
                            examples = @ExampleObject(value = """
                        {
                            "name": "Engineering Updated",
                            "bossId": "770f0600-g41d-63f6-c938-668877662222"
                        }
                    """)
                    )
            )
            @RequestBody UpdateDepartmentRequest req) {
        return ResponseEntity.ok(adminService.updateDepartment(id, req));
    }

    @Operation(
            summary = "Delete a department",
            description = "Deletes a department and soft deletes all users belonging to it."
    )
    @ApiResponses({
            @ApiResponse(responseCode = "204", description = "Department deleted successfully"),
            @ApiResponse(responseCode = "401", description = "Unauthorized"),
            @ApiResponse(responseCode = "403", description = "Forbidden — ADMIN only"),
            @ApiResponse(responseCode = "404", description = "Department not found")
    })
    @DeleteMapping("/departments/{id}")
    public ResponseEntity<Void> deleteDepartment(
            @Parameter(description = "UUID of the department to delete", example = "dept-uuid-123")
            @PathVariable String id) {
        adminService.deleteDepartment(id);
        return ResponseEntity.noContent().build();
    }

    @Operation(
            summary = "Get all departments",
            description = "Returns a list of all departments with their assigned boss info."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "List of departments returned successfully",
                    content = @Content(
                            mediaType = "application/json",
                            examples = @ExampleObject(value = """
                    [
                        {
                            "id": "dept-uuid-123",
                            "name": "Engineering",
                            "bossId": "660e9500-f30c-52e5-b827-557766551111",
                            "bossName": "Jane Smith",
                            "createdAtDateTime": "2026-04-20T09:00:00"
                        },
                        {
                            "id": "dept-uuid-456",
                            "name": "Finance",
                            "bossId": "770f0600-g41d-63f6-c938-668877662222",
                            "bossName": "Bob Johnson",
                            "createdAtDateTime": "2026-04-19T08:00:00"
                        }
                    ]
                """)
                    )
            ),
            @ApiResponse(responseCode = "401", description = "Unauthorized"),
            @ApiResponse(responseCode = "403", description = "Forbidden — ADMIN only")
    })
    @GetMapping("/departments")
    public ResponseEntity<List<DepartmentResponse>> getAllDepartments() {
        return ResponseEntity.ok(adminService.getAllDepartments());
    }

    @Operation(
            summary = "Get department by ID",
            description = "Returns a single department by its UUID, including boss details."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "Department found",
                    content = @Content(
                            mediaType = "application/json",
                            examples = @ExampleObject(value = """
                    {
                        "id": "dept-uuid-123",
                        "name": "Engineering",
                        "bossId": "660e9500-f30c-52e5-b827-557766551111",
                        "bossName": "Jane Smith",
                        "createdAtDateTime": "2026-04-20T09:00:00"
                    }
                """)
                    )
            ),
            @ApiResponse(responseCode = "401", description = "Unauthorized"),
            @ApiResponse(responseCode = "403", description = "Forbidden — ADMIN only"),
            @ApiResponse(responseCode = "404", description = "Department not found")
    })
    @GetMapping("/departments/{id}")
    public ResponseEntity<DepartmentResponse> getDepartmentById(
            @Parameter(description = "UUID of the department", example = "dept-uuid-123")
            @PathVariable String id) {
        return ResponseEntity.ok(adminService.getDepartmentById(id));
    }
}