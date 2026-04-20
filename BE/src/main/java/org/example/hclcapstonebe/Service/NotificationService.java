package org.example.hclcapstonebe.Service;


import org.example.hclcapstonebe.DTO.Response.NotificationResponse;
import org.example.hclcapstonebe.Entities.Notification;
import org.example.hclcapstonebe.Exception.AppException;
import org.example.hclcapstonebe.Mapper.NotificationMapper;
import org.example.hclcapstonebe.Repository.NotificationRepository;
import org.example.hclcapstonebe.Repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class NotificationService {

    private final NotificationRepository notificationRepository;
    private final UserRepository userRepository;
    private final NotificationMapper notificationMapper;    // MapStruct

    public List<NotificationResponse> getMyNotifications(String email) {
        var user = userRepository.findByEmailAndIsDeletedFalse(email)
                .orElseThrow(() -> new AppException("User not found", HttpStatus.NOT_FOUND));

        return notificationRepository
                .findByReceiverIdOrderByCreatedAtDesc(user.getId())
                .stream()
                .map(notificationMapper::toResponse)        // MapStruct method reference
                .collect(Collectors.toList());
    }

    public NotificationResponse markAsRead(String notifId, String email) {
        var user = userRepository.findByEmailAndIsDeletedFalse(email)
                .orElseThrow(() -> new AppException("User not found", HttpStatus.NOT_FOUND));

        Notification notif = notificationRepository.findById(notifId)
                .orElseThrow(() -> new AppException("Notification not found", HttpStatus.NOT_FOUND));

        // RBAC: only the receiver can mark as read
        if (!notif.getReceiver().getId().equals(user.getId())) {
            throw new AppException("Access denied", HttpStatus.FORBIDDEN);
        }

        notif.setHasRead(true);
        notif.setIsReadDateTime(LocalDateTime.now());
        notificationRepository.save(notif);

        return notificationMapper.toResponse(notif);        // MapStruct
    }
}