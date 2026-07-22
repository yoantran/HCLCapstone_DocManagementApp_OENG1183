package org.example.hclcapstonebe.Service;
import org.example.hclcapstonebe.DTO.Request.*;
import org.example.hclcapstonebe.DTO.Response.DepartmentResponse;
import org.example.hclcapstonebe.DTO.Response.UserProfileResponse;
import org.example.hclcapstonebe.Entities.Department;
import org.example.hclcapstonebe.Entities.User;
import org.example.hclcapstonebe.Enums.RoleEnum;
import org.example.hclcapstonebe.Exception.AppException;
import org.example.hclcapstonebe.Mapper.DepartmentMapper;
import org.example.hclcapstonebe.Mapper.UserMapper;
import org.example.hclcapstonebe.Repository.DepartmentRepository;
import org.example.hclcapstonebe.Repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.crossstore.ChangeSetPersister;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.example.hclcapstonebe.Exception.BadRequestException;
import org.example.hclcapstonebe.Exception.ConflictException;
import org.example.hclcapstonebe.Exception.NotFoundException;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class AdminService {

    private final UserRepository userRepository;
    private final DepartmentRepository departmentRepository;
    private final PasswordEncoder passwordEncoder;
    private final UserMapper userMapper;
    private final DepartmentMapper departmentMapper;

    // ─── USER ─────────────────────────────────────────────

    // ─── CREATE USER ──────────────────────────────────────
    public UserProfileResponse createUser(CreateUserRequest req) {
        if (userRepository.existsByEmail(req.getEmail())) {
            throw new AppException("Email already in use", HttpStatus.CONFLICT);
        }

        Department dept = null;
        if (req.getDepartmentId() != null) {
            dept = departmentRepository.findById(req.getDepartmentId())
                    .orElseThrow(() -> new AppException("Department not found", HttpStatus.NOT_FOUND));
        }

        User user = userMapper.toEntity(req);
        user.setDepartment(dept);
        user.setPassword(passwordEncoder.encode(req.getPassword()));
        user.setCreatedAtDateTime(LocalDateTime.now());

        // update department's manager if role = manager
        if (user.getRole() == RoleEnum.MANAGER && dept != null) {
            if (dept.getManager() != null) {
                throw new AppException("Department already has a manager", HttpStatus.BAD_REQUEST);
            }
            user = userRepository.save(user);
            dept.setManager(user);
            departmentRepository.save(dept);
        } else {
            user = userRepository.save(user);
        }

        return userMapper.toResponse(user);
    }
    @Transactional
    public UserProfileResponse reassignUser(UUID userId, ReassignUserRequest req) {

        User user = userRepository.findByIdAndIsDeletedFalse(userId)
                .orElseThrow(() -> new NotFoundException("User not found: " + userId));

        boolean removing = req.getDepartmentId() == null ;

        // A manager cannot be moved or orphaned by this endpoint — demote first.
        if (user.getRole() == RoleEnum.MANAGER) {
            throw new BadRequestException(
                    "User is a MANAGER of a department. Demote them via PATCH /admin/users/{id}/role "
                            + "before reassigning, or replace the manager via PUT /admin/departments/{id}.");
        }

        if (removing) {
            user.setDepartment(null);
        } else {
            Department dept = departmentRepository.findById(UUID.fromString(String.valueOf(req.getDepartmentId())))
                    .orElseThrow(() -> new NotFoundException("Department not found"));
            user.setDepartment(dept);
        }

        return userMapper.toResponse(userRepository.save(user));

    }
    @Transactional
    public UserProfileResponse assignDepartmentToUser(UUID userId, ReassignUserRequest req) {
        User user = userRepository.findByIdAndIsDeletedFalse(userId)
                .orElseThrow(() -> new AppException("User not found", HttpStatus.NOT_FOUND));

        if (user.getRole() == RoleEnum.MANAGER) {
            throw new AppException(
                    "Cannot assign department to a manager here. Use Update Department API to assign a manager to a department.",
                    HttpStatus.BAD_REQUEST
            );
        }

        if (req.getDepartmentId() != null) {
            Department newDept = departmentRepository.findById(req.getDepartmentId())
                    .orElseThrow(() -> new AppException("Department not found", HttpStatus.NOT_FOUND));
            user.setDepartment(newDept);
        } else {
            // empty string or null → remove from department
            user.setDepartment(null);
        }

        return userMapper.toResponse(userRepository.save(user));
    }



    @Transactional
    public UserProfileResponse changeRole(UUID userId, ChangeRoleRequest req) {

        User user = userRepository.findByIdAndIsDeletedFalse(userId)
                .orElseThrow(() -> new NotFoundException("User not found: " + userId));

        if (user.getRole() == req.getRole()) {
            throw new BadRequestException("User already has role " + req.getRole());
        }

        return req.getRole() == RoleEnum.MANAGER
                ? promote(user, req.getDepartmentId())
                : demote(user);
    }

    private UserProfileResponse promote(User user, String requestedDeptId) {

        Department dept;

        if (user.getDepartment() != null) {
            dept = user.getDepartment();
            // Guard against a silent no-op if FE sends a conflicting department.
            if (requestedDeptId != null && !requestedDeptId.isBlank()
                    && !dept.getId().toString().equals(requestedDeptId)) {
                throw new BadRequestException(
                        "User already belongs to department " + dept.getId()
                                + ". Reassign them first if you want them to manage a different one.");
            }
        } else {
            if (requestedDeptId == null || requestedDeptId.isBlank()) {
                throw new BadRequestException(
                        "User has no department. departmentId is required to promote.");
            }
            dept = departmentRepository.findById(UUID.fromString(requestedDeptId))
                    .orElseThrow(() -> new NotFoundException("Department not found"));
        }

        // Displace the incumbent: demote to STAFF, keep them in the department.
        User incumbent = dept.getManager();
        if (incumbent != null && !incumbent.getId().equals(user.getId())) {
            incumbent.setRole(RoleEnum.STAFF);
            userRepository.save(incumbent);
        }

        user.setDepartment(dept);
        user.setRole(RoleEnum.MANAGER);
        userRepository.save(user);
        dept.setManager(user);
        departmentRepository.save(dept);
        return userMapper.toResponse(user);
    }

    private UserProfileResponse demote(User user) {

        Department dept = user.getDepartment();

        // Detach from the department's manager slot, but stay in the department as STAFF.
        if (dept != null && dept.getManager() != null
                && dept.getManager().getId().equals(user.getId())) {
            dept.setManager(null);
            departmentRepository.save(dept);
        }

        user.setRole(RoleEnum.STAFF);
        userRepository.save(user);
        return userMapper.toResponse(user);
    }
    @Transactional
    public void deleteUser(UUID userId) {
        User user = userRepository.findByIdAndIsDeletedFalse(userId)
                .orElseThrow(() -> new AppException("User not found", HttpStatus.NOT_FOUND));

        // If user is a manager → auto clear department's manager
        if (user.getRole() == RoleEnum.MANAGER && user.getDepartment() != null) {
            Department dept = user.getDepartment();
            if (dept.getManager() != null && dept.getManager().getId().equals(userId)) {
                dept.setManager(null);
                departmentRepository.save(dept);
            }
        }

        // Clear user's department
        user.setDepartment(null);

        // Soft delete
        user.setDeleted(true);
        user.setDeletedAt(LocalDateTime.now());
        userRepository.save(user);
    }

    public List<UserProfileResponse> getAllUsers() {
        return userRepository.findByIsDeletedFalse()
                .stream()
                .map(userMapper::toResponse)                // MapStruct method reference
                .collect(Collectors.toList());
    }

    public UserProfileResponse getUserById(UUID id) {
        User user = userRepository.findByIdAndIsDeletedFalse(id)
                .orElseThrow(() -> new AppException("User not found", HttpStatus.NOT_FOUND));
        return userMapper.toResponse(user);                 // MapStruct
    }

    // ─── DEPARTMENT ───────────────────────────────────────

    // ─── CREATE DEPARTMENT ────────────────────────────────
    @Transactional
    public DepartmentResponse createDepartment(CreateDepartmentRequest req) {
        // manager is optional on creation
        User manager = null;
        if (req.getManagerId() != null) {
            manager = userRepository.findByIdAndIsDeletedFalse(UUID.fromString(req.getManagerId()))
                    .orElseThrow(() -> new AppException("manager user not found", HttpStatus.NOT_FOUND));

            if (manager.getRole() != RoleEnum.MANAGER) {
                throw new AppException("Assigned user is not a manager", HttpStatus.BAD_REQUEST);
            }

            // 1 user can only be manager of 1 department
            if (manager.getDepartment() != null) {
                throw new AppException(
                        "User is already manager of department: " + manager.getDepartment().getName(),
                        HttpStatus.CONFLICT
                );
            }
        }

        Department dept = departmentMapper.toEntity(req);
        dept.setManager(manager);                                          // can be null
        dept.setCreatedAtDateTime(LocalDateTime.now());
        Department saved = departmentRepository.save(dept);

        // Assign department back to manager user
        if (manager != null) {
            manager.setDepartment(saved);
            userRepository.save(manager);
        }

        return departmentMapper.toResponse(saved);
    }
    @Transactional
    public DepartmentResponse updateDepartment(UUID deptId, UpdateDepartmentRequest req) {
        Department dept = departmentRepository.findById(deptId)
                .orElseThrow(() -> new AppException("Department not found", HttpStatus.NOT_FOUND));

        // ── Update name ────────────────────────────────────
        if (req.getName() != null) {
            dept.setName(req.getName());
        }

        // ── Remove manager (managerId sent as "" or removemanager=true) ──
        boolean isRemovemanager = req.isRemovemanager()
                || (req.getManagerId() != null && req.getManagerId().isBlank());

        if (isRemovemanager) {
            User oldmanager = dept.getManager();
            if (oldmanager != null) {
                // Demote to STAFF — stays in the department
                oldmanager.setRole(RoleEnum.STAFF);
                userRepository.save(oldmanager);
            }
            dept.setManager(null);
            departmentRepository.save(dept);

            // ── Assign or replace manager (auto-promotes STAFF) ─────────────
        } else if (req.getManagerId() != null && !req.getManagerId().isBlank()) {
            User newmanager = userRepository.findByIdAndIsDeletedFalse(UUID.fromString(req.getManagerId()))
                    .orElseThrow(() -> new AppException("New manager not found", HttpStatus.NOT_FOUND));

            // A MANAGER of another department must be demoted there first.
            // A STAFF from another department is fine — they get moved and promoted.
            if (newmanager.getRole() == RoleEnum.MANAGER
                    && newmanager.getDepartment() != null
                    && !newmanager.getDepartment().getId().equals(deptId)) {
                throw new AppException(
                        "This user is already manager of: " + newmanager.getDepartment().getName(),
                        HttpStatus.CONFLICT
                );
            }

            // Step 1: Demote the incumbent — stays in the department as STAFF
            User oldmanager = dept.getManager();
            if (oldmanager != null && !oldmanager.getId().equals(newmanager.getId())) {
                oldmanager.setRole(RoleEnum.STAFF);
                userRepository.save(oldmanager);
            }

            // Step 2: Clear dept manager temporarily (handles circular FK)
            dept.setManager(null);
            departmentRepository.saveAndFlush(dept);

            // Step 3: Promote + assign the new manager
            newmanager.setDepartment(dept);
            newmanager.setRole(RoleEnum.MANAGER);
            userRepository.saveAndFlush(newmanager);

            // Step 4: Point the department at the new manager
            dept.setManager(newmanager);
            departmentRepository.save(dept);
        }
        // else: managerId is null → not sent → keep manager unchanged

        return departmentMapper.toResponse(departmentRepository.save(dept));
    }
    @Transactional
    public void deleteDepartment(UUID deptId) {
        Department dept = departmentRepository.findById(deptId)
                .orElseThrow(() -> new AppException("Department not found", HttpStatus.NOT_FOUND));

        // Step 1: Set all users in this department → department = null
        List<User> users = userRepository.findByDepartmentIdAndIsDeletedFalse(deptId);
        users.forEach(u -> u.setDepartment(null));
        userRepository.saveAll(users);

        // Step 2: Remove manager from department (avoids FK constraint on delete)
        dept.setManager(null);
        departmentRepository.save(dept);

        // Step 3: Delete the department
        departmentRepository.delete(dept);
    }

    public List<DepartmentResponse> getAllDepartments() {
        return departmentRepository.findAll()
                .stream()
                .map(departmentMapper::toResponse)          // MapStruct method reference
                .collect(Collectors.toList());
    }

    public DepartmentResponse getDepartmentById(UUID id) {
        Department dept = departmentRepository.findById(id)
                .orElseThrow(() -> new AppException("Department not found", HttpStatus.NOT_FOUND));
        return departmentMapper.toResponse(dept);           // MapStruct
    }
}