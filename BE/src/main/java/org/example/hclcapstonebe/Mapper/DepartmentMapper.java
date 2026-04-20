package org.example.hclcapstonebe.Mapper;


import org.example.hclcapstonebe.DTO.Request.CreateDepartmentRequest;
import org.example.hclcapstonebe.DTO.Response.DepartmentResponse;
import org.example.hclcapstonebe.Entities.Department;
import org.mapstruct.*;

@Mapper(componentModel = "spring")
public interface DepartmentMapper {

    @Mapping(source = "boss.id",   target = "bossId")
    @Mapping(source = "boss.name", target = "bossName")
    DepartmentResponse toResponse(Department department);

    @Mapping(target = "id",                ignore = true)
    @Mapping(target = "createdAtDateTime", ignore = true)
    @Mapping(target = "boss",              ignore = true) // set manually in service
    Department toEntity(CreateDepartmentRequest request);
}