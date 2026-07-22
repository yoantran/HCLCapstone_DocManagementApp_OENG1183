package org.example.hclcapstonebe.DTO.Request;


import lombok.Data;
import java.util.UUID;

@Data
public class ReassignUserRequest {
    private UUID departmentId;  // only field — assign or reassign department
}
