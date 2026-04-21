package org.example.hclcapstonebe.Service;
import org.example.hclcapstonebe.DTO.Request.AssignDepartmentRequest;
import org.example.hclcapstonebe.DTO.Request.CreateDepartmentRequest;
import org.example.hclcapstonebe.DTO.Request.CreateUserRequest;
import org.example.hclcapstonebe.DTO.Request.UpdateDepartmentRequest;
import org.example.hclcapstonebe.DTO.Response.DepartmentResponse;
import org.example.hclcapstonebe.DTO.Response.UserResponse;
import org.example.hclcapstonebe.Entities.Department;
import org.example.hclcapstonebe.Entities.User;
import org.example.hclcapstonebe.Enums.RoleEnum;
import org.example.hclcapstonebe.Exception.AppException;
import org.example.hclcapstonebe.Mapper.DepartmentMapper;
import org.example.hclcapstonebe.Mapper.UserMapper;
import org.example.hclcapstonebe.Repository.DepartmentRepository;
import org.example.hclcapstonebe.Repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
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
    public UserResponse createUser(CreateUserRequest req) {
        if (userRepository.existsByEmail(req.getEmail())) {
            throw new AppException("Email already in use", HttpStatus.CONFLICT);
        }

        Department dept = null;
        if (req.getDepartmentId() != null && !req.getDepartmentId().isBlank()) {
            dept = departmentRepository.findById(req.getDepartmentId())
                    .orElseThrow(() -> new AppException("Department not found", HttpStatus.NOT_FOUND));
        }

        User user = userMapper.toEntity(req);
        user.setDepartment(dept);
        user.setPassword(passwordEncoder.encode(req.getPassword()));
        user.setCreatedAtDateTime(LocalDateTime.now());

        return userMapper.toResponse(userRepository.save(user));
    }
    @Transactional
    public UserResponse assignDepartmentToUser(String userId, AssignDepartmentRequest req) {
        User user = userRepository.findByIdAndIsDeletedFalse(userId)
                .orElseThrow(() -> new AppException("User not found", HttpStatus.NOT_FOUND));

        if (user.getRoleEnum() == RoleEnum.BOSS) {
            throw new AppException(
                    "Cannot assign department to a BOSS here. Use Update Department API to assign a boss to a department.",
                    HttpStatus.BAD_REQUEST
            );
        }

        if (req.getDepartmentId() != null && !req.getDepartmentId().isBlank()) {
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
    public void deleteUser(String userId) {
        User user = userRepository.findByIdAndIsDeletedFalse(userId)
                .orElseThrow(() -> new AppException("User not found", HttpStatus.NOT_FOUND));

        // If user is a BOSS → auto clear department's boss
        if (user.getRoleEnum() == RoleEnum.BOSS && user.getDepartment() != null) {
            Department dept = user.getDepartment();
            if (dept.getBoss() != null && dept.getBoss().getId().equals(userId)) {
                dept.setBoss(null);
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

    public List<UserResponse> getAllUsers() {
        return userRepository.findByIsDeletedFalse()
                .stream()
                .map(userMapper::toResponse)                // MapStruct method reference
                .collect(Collectors.toList());
    }

    public UserResponse getUserById(String id) {
        User user = userRepository.findByIdAndIsDeletedFalse(id)
                .orElseThrow(() -> new AppException("User not found", HttpStatus.NOT_FOUND));
        return userMapper.toResponse(user);                 // MapStruct
    }

    // ─── DEPARTMENT ───────────────────────────────────────

    // ─── CREATE DEPARTMENT ────────────────────────────────
    @Transactional
    public DepartmentResponse createDepartment(CreateDepartmentRequest req) {
        // Boss is optional on creation
        User boss = null;
        if (req.getBossId() != null) {
            boss = userRepository.findByIdAndIsDeletedFalse(req.getBossId())
                    .orElseThrow(() -> new AppException("Boss user not found", HttpStatus.NOT_FOUND));

            if (boss.getRoleEnum() != RoleEnum.BOSS) {
                throw new AppException("Assigned user is not a BOSS", HttpStatus.BAD_REQUEST);
            }

            // 1 user can only be boss of 1 department
            if (boss.getDepartment() != null) {
                throw new AppException(
                        "User is already boss of department: " + boss.getDepartment().getName(),
                        HttpStatus.CONFLICT
                );
            }
        }

        Department dept = departmentMapper.toEntity(req);
        dept.setBoss(boss);                                          // can be null
        dept.setCreatedAtDateTime(LocalDateTime.now());
        Department saved = departmentRepository.save(dept);

        // Assign department back to boss user
        if (boss != null) {
            boss.setDepartment(saved);
            userRepository.save(boss);
        }

        return departmentMapper.toResponse(saved);
    }


    @Transactional
    public DepartmentResponse updateDepartment(String deptId, UpdateDepartmentRequest req) {
        Department dept = departmentRepository.findById(deptId)
                .orElseThrow(() -> new AppException("Department not found", HttpStatus.NOT_FOUND));

        // ── Update name ────────────────────────────────────
        if (req.getName() != null) {
            dept.setName(req.getName());
        }

        // ── Remove boss (bossId sent as "" or removeBoss=true) ──
        boolean isRemoveBoss = req.isRemoveBoss()
                || (req.getBossId() != null && req.getBossId().isBlank());

        if (isRemoveBoss) {
            User oldBoss = dept.getBoss();
            if (oldBoss != null) {
                // Old boss's department → null
                oldBoss.setDepartment(null);
                userRepository.save(oldBoss);
            }
            // Department's boss → null
            dept.setBoss(null);
            departmentRepository.save(dept);

            // ── Assign or replace boss ─────────────────────────
        } else if (req.getBossId() != null && !req.getBossId().isBlank()) {
            User newBoss = userRepository.findByIdAndIsDeletedFalse(req.getBossId())
                    .orElseThrow(() -> new AppException("New boss not found", HttpStatus.NOT_FOUND));

            if (newBoss.getRoleEnum() != RoleEnum.BOSS) {
                throw new AppException("Assigned user is not a BOSS", HttpStatus.BAD_REQUEST);
            }

            // 1 user can only be boss of 1 department
            if (newBoss.getDepartment() != null
                    && !newBoss.getDepartment().getId().equals(deptId)) {
                throw new AppException(
                        "This user is already boss of: " + newBoss.getDepartment().getName(),
                        HttpStatus.CONFLICT
                );
            }

            // Step 1: Old boss's department → null
            User oldBoss = dept.getBoss();
            if (oldBoss != null && !oldBoss.getId().equals(newBoss.getId())) {
                oldBoss.setDepartment(null);
                userRepository.save(oldBoss);
            }

            // Step 2: Clear dept boss temporarily (handles circular FK)
            dept.setBoss(null);
            departmentRepository.save(dept);

            // Step 3: Assign new boss to department
            dept.setBoss(newBoss);
            departmentRepository.save(dept);

            // Step 4: Assign department to new boss
            newBoss.setDepartment(dept);
            userRepository.save(newBoss);
        }
        // else: bossId is null → not sent → keep boss unchanged

        return departmentMapper.toResponse(departmentRepository.save(dept));
    }

    @Transactional
    public void deleteDepartment(String deptId) {
        Department dept = departmentRepository.findById(deptId)
                .orElseThrow(() -> new AppException("Department not found", HttpStatus.NOT_FOUND));

        // Step 1: Set all users in this department → department = null
        List<User> users = userRepository.findByDepartmentIdAndIsDeletedFalse(deptId);
        users.forEach(u -> u.setDepartment(null));
        userRepository.saveAll(users);

        // Step 2: Remove boss from department (avoids FK constraint on delete)
        dept.setBoss(null);
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

    public DepartmentResponse getDepartmentById(String id) {
        Department dept = departmentRepository.findById(id)
                .orElseThrow(() -> new AppException("Department not found", HttpStatus.NOT_FOUND));
        return departmentMapper.toResponse(dept);           // MapStruct
    }
}