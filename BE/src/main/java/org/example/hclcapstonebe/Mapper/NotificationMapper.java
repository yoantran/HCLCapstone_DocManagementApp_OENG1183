package org.example.hclcapstonebe.Mapper;

import org.example.hclcapstonebe.DTO.Response.NotificationResponse;
import org.example.hclcapstonebe.Entities.Notification;
import org.mapstruct.*;

@Mapper(componentModel = "spring")
public interface NotificationMapper {

    @Mapping(source = "triggeredDocument.id",   target = "triggeredDocumentId")
    @Mapping(source = "triggeredDocument.name", target = "triggeredDocumentName")
    @Mapping(source = "hasRead",                   target = "hasRead")  // ← both sides "isread"
    NotificationResponse toResponse(Notification notification);
}