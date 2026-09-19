package org.example.hclcapstonebe.Service;

import org.example.hclcapstonebe.DTO.Request.*;
import org.example.hclcapstonebe.DTO.Response.DepartmentResponse;
import org.example.hclcapstonebe.DTO.Response.UserProfileResponse;
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
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.transaction.annotation.Transactional;

import java.lang.reflect.Method;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

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

    // user management
    @Test
    void userManagement_createGetDeleteFlows() throws NoSuchMethodException {
        // Annotation check
        Method createUser = AdminService.class.getMethod("createUser", CreateUserRequest.class);
        assertTrue(createUser.isAnnotationPresent(Transactional.class));

        UUID userId = UUID.randomUUID();
        User mockUser = buildUser(userId, RoleEnum.STAFF);

        when(userMapper.toResponse(any())).thenReturn(new UserProfileResponse());
        when(userRepository.findByIsDeletedFalse()).thenReturn(List.of(mockUser));
        when(userRepository.findByIdAndIsDeletedFalse(userId)).thenReturn(Optional.of(mockUser));

        assertAll("User Management Operations",
                () -> {
                    // Create Staff User
                    CreateUserRequest req = new CreateUserRequest();
                    req.setEmail("test@example.com");
                    req.setPassword("password123");
                    req.setRoleEnum(RoleEnum.STAFF);

                    when(passwordEncoder.encode(any())).thenReturn("hashed");
                    when(userMapper.toEntity(any())).thenReturn(mockUser);
                    when(userRepository.save(any())).thenReturn(mockUser);

                    assertNotNull(adminService.createUser(req));
                },
                () -> {
                    // Get All & Get By ID
                    assertEquals(1, adminService.getAllUsers().size());
                    assertNotNull(adminService.getUserById(userId));
                },
                () -> {
                    // Soft Delete
                    adminService.deleteUser(userId);
                    assertTrue(mockUser.isDeleted());
                }
        );
    }

    @Test
    void userReassignmentAndManagerDeleteCleanup() {
        UUID userId = UUID.randomUUID();
        UUID deptId = UUID.randomUUID();

        User staffUser = buildUser(userId, RoleEnum.STAFF);
        Department dept = new Department();
        dept.setId(deptId);

        when(userRepository.findByIdAndIsDeletedFalse(userId)).thenReturn(Optional.of(staffUser));
        when(departmentRepository.findById(deptId)).thenReturn(Optional.of(dept));
        when(userRepository.save(any())).thenReturn(staffUser);
        when(userMapper.toResponse(any())).thenReturn(new UserProfileResponse());

        assertAll("User Reassignment Logic",
                () -> {
                    // Move to new department
                    ReassignUserRequest req = new ReassignUserRequest();
                    req.setDepartmentId(deptId);
                    assertNotNull(adminService.reassignUser(userId, req));
                    assertEquals(dept, staffUser.getDepartment());
                },
                () -> {
                    // Remove from department
                    ReassignUserRequest req = new ReassignUserRequest();
                    req.setDepartmentId(null);
                    assertNotNull(adminService.reassignUser(userId, req));
                    assertNull(staffUser.getDepartment());
                },
                () -> {
                    // Delete Manager User clears department slot
                    User managerUser = buildUser(userId, RoleEnum.MANAGER);
                    dept.setManager(managerUser);
                    managerUser.setDepartment(dept);

                    when(userRepository.findByIdAndIsDeletedFalse(userId)).thenReturn(Optional.of(managerUser));
                    adminService.deleteUser(userId);

                    assertTrue(managerUser.isDeleted());
                    assertNull(dept.getManager());
                }
        );
    }

    // role & promote
    @Test
    void changeRole_promotionAndDemotionFlows() {
        UUID userId = UUID.randomUUID();
        UUID deptId = UUID.randomUUID();

        User staffUser = buildUser(userId, RoleEnum.STAFF);
        Department dept = new Department();
        dept.setId(deptId);

        when(userRepository.findByIdAndIsDeletedFalse(userId)).thenReturn(Optional.of(staffUser));
        when(departmentRepository.findById(deptId)).thenReturn(Optional.of(dept));
        when(userRepository.save(any())).thenReturn(staffUser);
        when(departmentRepository.save(any())).thenReturn(dept);
        when(userMapper.toResponse(any())).thenReturn(new UserProfileResponse());

        assertAll("Role Mutations",
                () -> {
                    // Promote to Manager
                    ChangeRoleRequest req = new ChangeRoleRequest();
                    req.setRole(RoleEnum.MANAGER);
                    req.setDepartmentId(deptId.toString());

                    assertNotNull(adminService.changeRole(userId, req));
                    assertEquals(RoleEnum.MANAGER, staffUser.getRole());
                },
                () -> {
                    // Demote to Staff
                    User managerUser = buildUser(userId, RoleEnum.MANAGER);
                    dept.setManager(managerUser);
                    managerUser.setDepartment(dept);

                    when(userRepository.findByIdAndIsDeletedFalse(userId)).thenReturn(Optional.of(managerUser));

                    ChangeRoleRequest req = new ChangeRoleRequest();
                    req.setRole(RoleEnum.STAFF);

                    assertNotNull(adminService.changeRole(userId, req));
                    assertEquals(RoleEnum.STAFF, managerUser.getRole());
                    assertNull(dept.getManager());
                }
        );
    }

    // department management
    @Test
    void departmentManagement_crudAndIncumbentDisplacement() {
        UUID deptId = UUID.randomUUID();
        Department dept = new Department();
        dept.setId(deptId);
        dept.setName("Old Name");

        User incumbent = buildUser(UUID.randomUUID(), RoleEnum.MANAGER);
        incumbent.setDepartment(dept);
        dept.setManager(incumbent);

        User newManager = buildUser(UUID.randomUUID(), RoleEnum.STAFF);

        when(departmentRepository.findById(deptId)).thenReturn(Optional.of(dept));
        when(departmentRepository.findAll()).thenReturn(List.of(dept));
        when(departmentRepository.save(any())).thenReturn(dept);
        when(departmentMapper.toResponse(any())).thenReturn(new DepartmentResponse());

        assertAll("Department CRUD",
                () -> {
                    CreateDepartmentRequest req = new CreateDepartmentRequest();
                    req.setName("Engineering");
                    when(departmentMapper.toEntity(any())).thenReturn(dept);
                    assertNotNull(adminService.createDepartment(req));
                },
                () -> {
                    assertEquals(1, adminService.getAllDepartments().size());
                    assertNotNull(adminService.getDepartmentById(deptId));
                },
                () -> {
                    UpdateDepartmentRequest req = new UpdateDepartmentRequest();
                    req.setName("New Name");
                    req.setManagerId(newManager.getId().toString());

                    when(userRepository.findByIdAndIsDeletedFalse(newManager.getId())).thenReturn(Optional.of(newManager));

                    assertNotNull(adminService.updateDepartment(deptId, req));
                    assertEquals("New Name", dept.getName());
                    assertEquals(newManager, dept.getManager());
                },
                () -> {
                    User userInDept = buildUser(UUID.randomUUID(), RoleEnum.STAFF);
                    userInDept.setDepartment(dept);
                    when(userRepository.findByDepartmentIdAndIsDeletedFalse(deptId)).thenReturn(List.of(userInDept));

                    adminService.deleteDepartment(deptId);
                    assertNull(userInDept.getDepartment());
                    verify(departmentRepository).delete(dept);
                }
        );
    }

    // validation & exception
    @Test
    void adminService_validationAndConflictErrors() {
        UUID adminId = UUID.randomUUID();
        User admin = buildUser(adminId, RoleEnum.ADMIN);

        when(userRepository.findByIdAndIsDeletedFalse(adminId)).thenReturn(Optional.of(admin));
        when(userRepository.existsByEmail("existing@hcl.com")).thenReturn(true);

        assertAll("Admin Service Validation Checks",
                () -> {
                    // Reject changing an ADMIN's role
                    ChangeRoleRequest req = new ChangeRoleRequest();
                    req.setRole(RoleEnum.MANAGER);
                    assertThrows(BadRequestException.class, () -> adminService.changeRole(adminId, req));
                },
                () -> {
                    // Duplicate email creation throws AppException(409 CONFLICT)
                    CreateUserRequest req = new CreateUserRequest();
                    req.setEmail("existing@hcl.com");
                    AppException ex = assertThrows(AppException.class, () -> adminService.createUser(req));
                    assertEquals(HttpStatus.CONFLICT, ex.getStatus());
                },
                () -> {
                    // Cannot assign an ADMIN as department manager
                    UUID deptId = UUID.randomUUID();
                    Department dept = new Department();
                    dept.setId(deptId);

                    UpdateDepartmentRequest req = new UpdateDepartmentRequest();
                    req.setManagerId(adminId.toString());

                    when(departmentRepository.findById(deptId)).thenReturn(Optional.of(dept));
                    AppException ex = assertThrows(AppException.class, () -> adminService.updateDepartment(deptId, req));
                    assertEquals(HttpStatus.BAD_REQUEST, ex.getStatus());
                }
        );
    }
}