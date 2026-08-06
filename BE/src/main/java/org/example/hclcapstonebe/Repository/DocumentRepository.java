package org.example.hclcapstonebe.Repository;


import org.example.hclcapstonebe.Entities.Document;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface DocumentRepository extends JpaRepository<Document, UUID> {

    @EntityGraph(attributePaths = {"uploader", "department"})
    List<Document> findByUploaderIdAndIsDeletedFalse(UUID uploaderId);

    @EntityGraph(attributePaths = {"uploader", "department"})
    List<Document> findByDepartmentIdAndIsDeletedFalse(UUID departmentId);

    @EntityGraph(attributePaths = {"uploader", "department"})
    Optional<Document> findByIdAndIsDeletedFalse(UUID id);
}