package org.example.hclcapstonebe.Repository;

import org.example.hclcapstonebe.Entities.Notification;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface NotificationRepository extends JpaRepository<Notification, String> {
    List<Notification> findByReceiverIdOrderByCreatedAtDesc(String receiverId);
}