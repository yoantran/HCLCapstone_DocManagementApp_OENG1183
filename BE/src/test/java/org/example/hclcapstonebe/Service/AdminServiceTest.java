package org.example.hclcapstonebe.Service;

import org.example.hclcapstonebe.DTO.Request.ChangeRoleRequest;
import org.example.hclcapstonebe.DTO.Request.UpdateDepartmentRequest;
import org.example.hclcapstonebe.Entities.Department;
import org.example.hclcapstonebe.Entities.User;
import org.example.hclcapstonebe.Enums.RoleEnum;
import org.example.hclcapstonebe.Exception.AppException;
import org.example.hclcapstonebe.Exception.BadRequestException;
import org.example.hclcapstonebe.Mapper.DepartmentMapper;
import org.example.hclcapstonebe.Mapper.UserMapper;
import org.example.hclcapstonebe.Repository.DepartmentRepository;
import org.example.hclcapstonebe.Repository.UserRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class AdminServiceTest {

    @Mock private UserRepository userRepository;
    @Mock private DepartmentRepository departmentRepository;
    @Mock private PasswordEncoder passwordEncoder;
    @Mock private UserMapper userMapper;
    @Mock private DepartmentMapper departmentMapper;

    @InjectMocks
    private AdminService adminService;

    private User buildUser(UUID id, RoleEnum role) {
        User user = new User();
        user.setId(id);
        user.setRole(role);
        return user;
    }

    // Real, confirmed bug: changeRole() only rejects a same-role no-op --
    // routing anything else straight to promote()/demote(), neither of
    // which checks the user's CURRENT role. PATCH .../role with
    // {role: MANAGER} on a real ADMIN silently demoted them, since
    // ADMIN != MANAGER passes the only guard that existed.
    @Test
    void changeRole_rejectsChangingAnAdmin() {
        UUID adminId = UUID.randomUUID();
        User admin = buildUser(adminId, RoleEnum.ADMIN);
        // Real department, so the pre-existing "no department, can't
        // promote" guard in promote() doesn't mask what this test is
        // actually checking -- rejecting an ADMIN target at all.
        Department dept = new Department();
        dept.setId(UUID.randomUUID());
        admin.setDepartment(dept);
        when(userRepository.findByIdAndIsDeletedFalse(adminId)).thenReturn(Optional.of(admin));

        ChangeRoleRequest req = new ChangeRoleRequest();
        req.setRole(RoleEnum.MANAGER);

        assertThrows(BadRequestException.class, () -> adminService.changeRole(adminId, req));

        verify(userRepository, never()).save(any());
    }

    // Real, confirmed bug: updateDepartment's manager-reassignment only
    // rejected a user already MANAGER of a different department -- never
    // checked for ADMIN, so assigning an admin's id as managerId silently
    // converted them to MANAGER.
    @Test
    void updateDepartment_rejectsAssigningAnAdminAsManager() {
        UUID deptId = UUID.randomUUID();
        UUID adminId = UUID.randomUUID();
        Department dept = new Department();
        dept.setId(deptId);
        User admin = buildUser(adminId, RoleEnum.ADMIN);

        when(departmentRepository.findById(deptId)).thenReturn(Optional.of(dept));
        when(userRepository.findByIdAndIsDeletedFalse(adminId)).thenReturn(Optional.of(admin));

        UpdateDepartmentRequest req = new UpdateDepartmentRequest();
        req.setManagerId(adminId.toString());

        assertThrows(AppException.class, () -> adminService.updateDepartment(deptId, req));

        verify(userRepository, never()).save(any());
    }
}
