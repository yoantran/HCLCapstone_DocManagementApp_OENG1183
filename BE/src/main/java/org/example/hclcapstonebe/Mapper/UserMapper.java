package org.example.hclcapstonebe.Mapper;


import org.example.hclcapstonebe.DTO.Request.CreateUserRequest;
import org.example.hclcapstonebe.DTO.Response.UserResponse;
import org.example.hclcapstonebe.Entities.User;
import org.mapstruct.*;

@Mapper(componentModel = "spring")
public interface UserMapper {

    @Mapping(source = "department.id",   target = "departmentId")
    @Mapping(source = "department.name", target = "departmentName")
        // roleEnum maps automatically — same name, same type everywhere
    UserResponse toResponse(User user);

    @Mapping(target = "id",                ignore = true)
    @Mapping(target = "createdAtDateTime", ignore = true)
    @Mapping(target = "avatarImageUrl",    ignore = true)
    @Mapping(target = "department",        ignore = true)
    @Mapping(target = "isDeleted",         ignore = true)
    @Mapping(target = "deletedAt",         ignore = true)
    User toEntity(CreateUserRequest request);
}

