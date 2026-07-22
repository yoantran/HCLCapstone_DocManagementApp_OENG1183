package org.example.hclcapstonebe.DTO.Request;


import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.Data;
import org.example.hclcapstonebe.Enums.RoleEnum;

@Data
@Schema(description = "Change a user's role. Promotion requires a department.")
public class ChangeRoleRequest {

    @NotNull
    @Schema(description = "Target role", example = "MANAGER", allowableValues = {"STAFF", "MANAGER"})
    private RoleEnum role;

    @Schema(
            description = "Required when promoting a user who has no department. "
                    + "Ignored when the user already belongs to a department, or when demoting.",
            example = "dept-uuid-123"
    )
    private String departmentId;
}
