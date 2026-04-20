package org.example.hclcapstonebe.Repository;


import org.example.hclcapstonebe.Entities.Document;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;

public interface DocumentRepository extends JpaRepository<Document, String> {
    // Staff/Boss: own docs
    List<Document> findByUploaderIdAndIsDeletedFalse(String uploaderId);
    // Boss: all department docs
    List<Document> findByDepartmentIdAndIsDeletedFalse(String departmentId);
    Optional<Document> findByIdAndIsDeletedFalse(String id);
}