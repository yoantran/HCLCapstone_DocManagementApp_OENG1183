package org.example.hclcapstonebe.Repository;

import org.example.hclcapstonebe.Entities.User;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface UserRepository extends JpaRepository<User, UUID> {

    @EntityGraph(attributePaths = {"department", "department.manager"})  // ← add department.manager
    Optional<User> findByEmailAndIsDeletedFalse(String email);

    @EntityGraph(attributePaths = {"department", "department.manager"})
    List<User> findByDepartmentIdAndIsDeletedFalse(UUID departmentId);

    @EntityGraph(attributePaths = {"department", "department.manager"})
    List<User> findByIsDeletedFalse();

    @EntityGraph(attributePaths = {"department", "department.manager"})
    Optional<User> findByIdAndIsDeletedFalse(UUID id);

    boolean existsByEmail(String email);
}