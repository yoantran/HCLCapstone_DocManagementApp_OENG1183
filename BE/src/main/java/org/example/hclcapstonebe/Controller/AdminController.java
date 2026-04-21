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
import org.example.hclcapstonebe.DTO.Request.AssignDepartmentRequest;
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

    @Operation(
            summary = "Create a new user",
            description = """
        Creates a new user (STAFF or BOSS). ADMIN only.

        **Rules:**
        - `departmentId` is optional — leave it out or send `""` to create without a department
        - 1 user can only belong to 1 department
        - 1 department can have many STAFFs but only 0 or 1 BOSS
        """
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "201",
                    description = "User created successfully",
                    content = @Content(
                            mediaType = "application/json",
                            schema = @Schema(implementation = UserResponse.class),
                            examples = {
                                    @ExampleObject(
                                            name = "Created with department",
                                            value = """
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "email": "john.doe@hcl.com",
                            "name": "John Doe",
                            "avatarImageUrl": null,
                            "phoneNumber": "0901234567",
                            "departmentId": "dept-uuid-123",
                            "roleEnum": "STAFF",
                            "createdAtDateTime": "2026-04-20T10:00:00"
                        }
                    """
                                    ),
                                    @ExampleObject(
                                            name = "Created without department",
                                            value = """
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "email": "jane.doe@hcl.com",
                            "name": "Jane Doe",
                            "avatarImageUrl": null,
                            "phoneNumber": "0901234567",
                            "departmentId": null,
                            "roleEnum": "BOSS",
                            "createdAtDateTime": "2026-04-20T10:00:00"
                        }
                    """
                                    )
                            }
                    )
            ),
            @ApiResponse(responseCode = "400", description = "Invalid request body or missing required fields"),
            @ApiResponse(responseCode = "401", description = "Unauthorized — JWT token missing or invalid"),
            @ApiResponse(responseCode = "403", description = "Forbidden — ADMIN only"),
            @ApiResponse(responseCode = "404", description = "Department not found"),
            @ApiResponse(responseCode = "409", description = "Email already in use")
    })
    @PostMapping("/users")
    public ResponseEntity<UserResponse> createUser(
            @io.swagger.v3.oas.annotations.parameters.RequestBody(
                    description = "User creation payload. `departmentId` is optional.",
                    required = true,
                    content = @Content(
                            examples = {
                                    @ExampleObject(
                                            name = "Create and assign department",
                                            value = """
                        {
                            "email": "john.doe@hcl.com",
                            "password": "securePassword123",
                            "name": "John Doe",
                            "phoneNumber": "0901234567",
                            "roleEnum": "STAFF",
                            "departmentId": "dept-uuid-123"
                        }
                    """
                                    ),
                                    @ExampleObject(
                                            name = "Create without department",
                                            value = """
                        {
                            "email": "jane.doe@hcl.com",
                            "password": "securePassword123",
                            "name": "Jane Doe",
                            "phoneNumber": "0901234567",
                            "roleEnum": "BOSS"
                        }
                    """
                                    )
                            }
                    )
            )
            @Valid @RequestBody CreateUserRequest req) {
        return ResponseEntity.status(HttpStatus.CREATED).body(adminService.createUser(req));
    }

    @Operation(
            summary = "Assign or reassign a STAFF to a department",
            description = """
        ADMIN only — assigns or reassigns a STAFF user to a department.

        **Rules:**
        - Only works for STAFF users — use **Update Department API** to assign a BOSS
        - Send `departmentId` with a valid UUID to assign or reassign
        - Send `departmentId` as `""` or `null` to remove from department

        **To assign a BOSS to a department:** use `PUT /admin/departments/{id}`
        """
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "Department assigned successfully",
                    content = @Content(
                            mediaType = "application/json",
                            examples = {
                                    @ExampleObject(
                                            name = "Assigned to department",
                                            value = """
                        {
                            "id": "user-uuid-123",
                            "email": "john.doe@hcl.com",
                            "name": "John Doe",
                            "avatarImageUrl": null,
                            "phoneNumber": "0901234567",
                            "departmentId": "dept-uuid-123",
                            "departmentName": "Engineering",
                            "roleEnum": "STAFF",
                            "createdAtDateTime": "2026-04-20T10:00:00"
                        }
                    """
                                    ),
                                    @ExampleObject(
                                            name = "Removed from department",
                                            value = """
                        {
                            "id": "user-uuid-123",
                            "email": "john.doe@hcl.com",
                            "name": "John Doe",
                            "avatarImageUrl": null,
                            "phoneNumber": "0901234567",
                            "departmentId": null,
                            "departmentName": null,
                            "roleEnum": "STAFF",
                            "createdAtDateTime": "2026-04-20T10:00:00"
                        }
                    """
                                    )
                            }
                    )
            ),
            @ApiResponse(responseCode = "400", description = "User is a BOSS — use Update Department API instead"),
            @ApiResponse(responseCode = "401", description = "Unauthorized"),
            @ApiResponse(responseCode = "403", description = "Forbidden — ADMIN only"),
            @ApiResponse(responseCode = "404", description = "User or department not found")
    })
    @PatchMapping("/users/{id}")
    public ResponseEntity<UserResponse> reassignStaff(
            @Parameter(description = "UUID of the STAFF user to assign", example = "user-uuid-123")
            @PathVariable String id,
            @io.swagger.v3.oas.annotations.parameters.RequestBody(
                    description = "Send `departmentId` to assign. Send empty string or omit to remove from department.",
                    content = @Content(
                            examples = {
                                    @ExampleObject(
                                            name = "Assign to department",
                                            value = "{ \"departmentId\": \"dept-uuid-123\" }"
                                    ),
                                    @ExampleObject(
                                            name = "Remove from department",
                                            value = "{ \"departmentId\": \"\" }"
                                    )
                            }
                    )
            )
            @RequestBody AssignDepartmentRequest req) {
        return ResponseEntity.ok(adminService.assignDepartmentToUser(id, req));
    }
    @Operation(
            summary = "Soft delete a user",
            description = """
        Soft deletes a user by setting isDeleted=true. The user record is NOT permanently removed.

        **If the deleted user is a BOSS:**
        - Their department's boss is automatically set to null
        - The user's department assignment is cleared
        - No manual reassignment needed before deletion
        """
    )
    @ApiResponses({
            @ApiResponse(responseCode = "204", description = "User deleted successfully"),
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
            description = """
        Creates a new department. ADMIN only.

        **Rules:**
        - `bossId` is optional — leave it out to create without a boss
        - 1 department can only have 0 or 1 boss
        - 1 user can only be the boss of 1 department
        - Assigned User must have BOSS role
        - Assigned Boss must NOT in any departments. If you want to assign this boss to the newly created department, 
        you must Update affected department => remove boss first. 
        """
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "201",
                    description = "Department created successfully",
                    content = @Content(
                            mediaType = "application/json",
                            examples = {
                                    @ExampleObject(
                                            name = "Created with boss",
                                            value = """
                        {
                            "id": "dept-uuid-123",
                            "name": "Engineering",
                            "bossId": "660e9500-f30c-52e5-b827-557766551111",
                            "bossName": "Jane Smith",
                            "createdAtDateTime": "2026-04-20T09:00:00"
                        }
                    """
                                    ),
                                    @ExampleObject(
                                            name = "Created without boss",
                                            value = """
                        {
                            "id": "dept-uuid-456",
                            "name": "Finance",
                            "bossId": null,
                            "bossName": null,
                            "createdAtDateTime": "2026-04-20T09:00:00"
                        }
                    """
                                    )
                            }
                    )
            ),
            @ApiResponse(responseCode = "400", description = "Assigned user is not a BOSS role"),
            @ApiResponse(responseCode = "401", description = "Unauthorized"),
            @ApiResponse(responseCode = "403", description = "Forbidden — ADMIN only"),
            @ApiResponse(responseCode = "404", description = "Boss user not found"),
            @ApiResponse(responseCode = "409", description = "User is already boss of another department")
    })
    @PostMapping("/departments")
    public ResponseEntity<DepartmentResponse> createDepartment(
            @io.swagger.v3.oas.annotations.parameters.RequestBody(
                    description = "Department creation payload. `bossId` is optional.",
                    required = true,
                    content = @Content(
                            examples = {
                                    @ExampleObject(
                                            name = "Create with boss",
                                            value = """
                        {
                            "name": "Engineering",
                            "bossId": "660e9500-f30c-52e5-b827-557766551111"
                        }
                    """
                                    ),
                                    @ExampleObject(
                                            name = "Create without boss",
                                            value = """
                        {
                            "name": "Finance"
                        }
                    """
                                    )
                            }
                    )
            )
            @Valid @RequestBody CreateDepartmentRequest req) {
        return ResponseEntity.status(HttpStatus.CREATED).body(adminService.createDepartment(req));
    }
    @Operation(
            summary = "Update a department",
            description = """
        Updates a department. All fields are optional — only send what you want to change.
        Unset fields keep their current value.

        **Update name only:**
        Send `name` field, omit `bossId`.

        **Replace boss:**
        Send `bossId` with a valid BOSS user UUID.
        → Old boss's department is set to null automatically.
        → New boss is assigned to this department.
        → New boss must not already be boss of another department.

        **Remove boss (no boss assigned):**
        Send `bossId` as empty string `""` OR send `removeBoss: true`.
        → Current boss's department is set to null.
        → Department's boss is set to null.

        **Add boss to a department that has no boss:**
        Send `bossId` with a valid BOSS user UUID — same as replacing boss.
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
            @ApiResponse(responseCode = "400", description = "Assigned user is not a BOSS role"),
            @ApiResponse(responseCode = "401", description = "Unauthorized"),
            @ApiResponse(responseCode = "403", description = "Forbidden — ADMIN only"),
            @ApiResponse(responseCode = "404", description = "Department or boss user not found"),
            @ApiResponse(responseCode = "409", description = "User is already boss of another department")
    })
    @PutMapping("/departments/{id}")
    public ResponseEntity<DepartmentResponse> updateDepartment(
            @Parameter(description = "UUID of the department to update", example = "dept-uuid-123")
            @PathVariable String id,
            @io.swagger.v3.oas.annotations.parameters.RequestBody(
                    description = "All fields optional. Only sent fields are updated.",
                    content = @Content(
                            examples = {
                                    @ExampleObject(name = "Update name only",
                                            value = """
            { "name": "Engineering Updated" }
            """),
                                    @ExampleObject(name = "Replace boss",
                                            value = """
            { "bossId": "770f0600-g41d-63f6-c938-668877662222" }
            """),
                                    @ExampleObject(name = "Remove boss",
                                            value = """
            { "bossId": "" }
            """),
                                    @ExampleObject(name = "Update name and replace boss",
                                            value = """
            { "name": "Engineering Updated", "bossId": "770f0600-g41d-63f6-c938-668877662222" }
            """)
                            }
                    )
            )
            @RequestBody UpdateDepartmentRequest req) {
        return ResponseEntity.ok(adminService.updateDepartment(id, req));
    }

    @Operation(
            summary = "Delete a department",
            description = """
        Deletes a department permanently.
        All users (boss and staff) that belonged to this department will have their
        department set to null — they are NOT deleted.
        """
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