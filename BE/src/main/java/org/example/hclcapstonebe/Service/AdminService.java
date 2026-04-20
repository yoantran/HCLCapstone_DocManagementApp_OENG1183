package org.example.hclcapstonebe.Service;
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

    public UserResponse createUser(CreateUserRequest req) {
        if (userRepository.existsByEmail(req.getEmail())) {
            throw new AppException("Email already in use", HttpStatus.CONFLICT);
        }

        Department dept = departmentRepository.findById(req.getDepartmentId())
                .orElseThrow(() -> new AppException("Department not found", HttpStatus.NOT_FOUND));

        User user = userMapper.toEntity(req);               // MapStruct
        user.setDepartment(dept);                           // set manually (needs DB lookup)
        user.setPassword(passwordEncoder.encode(req.getPassword())); // encode manually

        return userMapper.toResponse(userRepository.save(user)); // MapStruct
    }

    @Transactional
    public void deleteUser(String userId) {
        User user = userRepository.findByIdAndIsDeletedFalse(userId)
                .orElseThrow(() -> new AppException("User not found", HttpStatus.NOT_FOUND));

        // If this user is a boss, block deletion until new boss is assigned
        if (user.getRoleEnum() == RoleEnum.BOSS) {
            Department dept = user.getDepartment();
            if (dept != null && dept.getBoss().getId().equals(userId)) {
                throw new AppException(
                        "Assign a new boss to department '" + dept.getName() + "' before deleting this boss.",
                        HttpStatus.BAD_REQUEST
                );
            }
        }

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

    @Transactional
    public DepartmentResponse createDepartment(CreateDepartmentRequest req) {
        User boss = userRepository.findByIdAndIsDeletedFalse(req.getBossId())
                .orElseThrow(() -> new AppException("Boss user not found", HttpStatus.NOT_FOUND));

        if (boss.getRoleEnum() != RoleEnum.BOSS) {
            throw new AppException("Assigned user is not a BOSS", HttpStatus.BAD_REQUEST);
        }

        Department dept = departmentMapper.toEntity(req);   // MapStruct
        dept.setBoss(boss);                                 // set manually (needs DB lookup)

        return departmentMapper.toResponse(departmentRepository.save(dept)); // MapStruct
    }

    @Transactional
    public DepartmentResponse updateDepartment(String deptId, UpdateDepartmentRequest req) {
        Department dept = departmentRepository.findById(deptId)
                .orElseThrow(() -> new AppException("Department not found", HttpStatus.NOT_FOUND));

        if (req.getName() != null) {
            dept.setName(req.getName());
        }

        // Reassign boss if requested
        if (req.getBossId() != null) {
            User newBoss = userRepository.findByIdAndIsDeletedFalse(req.getBossId())
                    .orElseThrow(() -> new AppException("New boss not found", HttpStatus.NOT_FOUND));

            if (newBoss.getRoleEnum() != RoleEnum.BOSS) {
                throw new AppException("Assigned user is not a BOSS", HttpStatus.BAD_REQUEST);
            }

            if (newBoss.getDepartment() == null ||
                    !newBoss.getDepartment().getId().equals(deptId)) {
                throw new AppException(
                        "New boss must belong to this department", HttpStatus.BAD_REQUEST);
            }

            dept.setBoss(newBoss);
        }

        return departmentMapper.toResponse(departmentRepository.save(dept)); // MapStruct
    }

    @Transactional
    public void deleteDepartment(String deptId) {
        Department dept = departmentRepository.findById(deptId)
                .orElseThrow(() -> new AppException("Department not found", HttpStatus.NOT_FOUND));

        // Soft delete all users in this department
        List<User> users = userRepository.findByDepartmentIdAndIsDeletedFalse(deptId);
        users.forEach(u -> {
            u.setDeleted(true);
            u.setDeletedAt(LocalDateTime.now());
        });
        userRepository.saveAll(users);

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