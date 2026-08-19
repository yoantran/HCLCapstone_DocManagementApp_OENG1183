package org.example.hclcapstonebe.Mapper;


import org.example.hclcapstonebe.DTO.Response.DocumentResponse;
import org.example.hclcapstonebe.Entities.Document;
import org.mapstruct.*;

@Mapper(componentModel = "spring")
public interface DocumentMapper {

    @Mapping(source = "uploader.id",     target = "uploaderId")
    @Mapping(source = "uploader.name",   target = "uploaderName")
    @Mapping(source = "department.id",   target = "departmentId")
    @Mapping(source = "department.name", target = "departmentName")
    @Mapping(source = "byteSize",        target = "byteSize")        // ← add this
    @Mapping(source = "type",            target = "type",   qualifiedByName = "enumToString")
    @Mapping(source = "format",          target = "format", qualifiedByName = "enumToString")
    @Mapping(target = "signedUrl",       ignore = true)
    @Mapping(target = "requesterIsOwner", ignore = true)
    @Mapping(target = "accessible",    ignore = true)
    DocumentResponse toResponse(Document document);

    @Named("enumToString")
    default String enumToString(Object value) {
        return value != null ? value.toString() : null;
    }
}
