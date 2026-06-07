package org.example.hclcapstonebe.Repository;

import org.example.hclcapstonebe.Entities.Notification;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface NotificationRepository extends JpaRepository<Notification, UUID> {

    @EntityGraph(attributePaths = {"triggeredDocument", "receiver"})
    List<Notification> findByReceiverIdOrderByCreatedAtDesc(UUID receiverId);

    @EntityGraph(attributePaths = {"triggeredDocument", "receiver"})
    Optional<Notification> findWithDetailsById(UUID id);   // ← custom name, EntityGraph works
}