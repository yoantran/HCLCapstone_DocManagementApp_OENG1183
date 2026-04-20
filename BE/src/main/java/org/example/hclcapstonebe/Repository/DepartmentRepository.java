package org.example.hclcapstonebe.Repository;


import org.example.hclcapstonebe.Entities.Department;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;

public interface DepartmentRepository extends JpaRepository<Department, String> {
    List<Department> findAll();
    Optional<Department> findById(String id);
}