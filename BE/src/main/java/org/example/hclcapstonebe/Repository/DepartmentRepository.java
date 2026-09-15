package org.example.hclcapstonebe.Repository;


import org.example.hclcapstonebe.Entities.Department;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.UUID;

public interface DepartmentRepository extends JpaRepository<Department, UUID> {
}