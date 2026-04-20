package org.example.hclcapstonebe.Repository;

import org.example.hclcapstonebe.Entities.User;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;

public interface UserRepository extends JpaRepository<User, String> {
    Optional<User> findByEmailAndIsDeletedFalse(String email);
    List<User> findByDepartmentIdAndIsDeletedFalse(String departmentId);
    List<User> findByIsDeletedFalse();
    Optional<User> findByIdAndIsDeletedFalse(String id);
    boolean existsByEmail(String email);
}