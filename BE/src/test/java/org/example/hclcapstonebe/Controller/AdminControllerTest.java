package org.example.hclcapstonebe.Controller;

import org.example.hclcapstonebe.DTO.Response.DepartmentResponse;
import org.example.hclcapstonebe.DTO.Response.UserProfileResponse;
import org.example.hclcapstonebe.Service.AdminService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.List;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@ExtendWith(MockitoExtension.class)
class AdminControllerTest {

    @Mock private AdminService adminService;
    @InjectMocks private AdminController adminController;

    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders.standaloneSetup(adminController).build();
    }

    @Test
    void adminUserOperations_executeSuccessfully() throws Exception {
        UUID userId = UUID.randomUUID();
        when(adminService.createUser(any())).thenReturn(new UserProfileResponse());
        when(adminService.reassignUser(any(), any())).thenReturn(new UserProfileResponse());
        when(adminService.getAllUsers()).thenReturn(List.of());
        when(adminService.getUserById(any())).thenReturn(new UserProfileResponse());
        when(adminService.changeRole(any(), any())).thenReturn(new UserProfileResponse());

        // Create User
        mockMvc.perform(post("/admin/users")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"test@hcl.com\",\"password\":\"pass\",\"name\":\"Test\",\"roleEnum\":\"STAFF\"}"))
                .andExpect(status().isCreated());

        // Reassign Department
        mockMvc.perform(patch("/admin/users/{id}/department", userId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"departmentId\":\"" + UUID.randomUUID() + "\"}"))
                .andExpect(status().isOk());

        // Delete, Get All, Get By ID, Change Role
        mockMvc.perform(delete("/admin/users/{id}", userId)).andExpect(status().isNoContent());
        mockMvc.perform(get("/admin/users")).andExpect(status().isOk());
        mockMvc.perform(get("/admin/users/{id}", userId)).andExpect(status().isOk());
        mockMvc.perform(patch("/admin/users/{id}/role", userId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"role\":\"MANAGER\"}"))
                .andExpect(status().isOk());
    }

    @Test
    void adminDepartmentOperations_executeSuccessfully() throws Exception {
        UUID deptId = UUID.randomUUID();
        when(adminService.createDepartment(any())).thenReturn(new DepartmentResponse());
        when(adminService.updateDepartment(any(), any())).thenReturn(new DepartmentResponse());
        when(adminService.getAllDepartments()).thenReturn(List.of());
        when(adminService.getDepartmentById(any())).thenReturn(new DepartmentResponse());

        // Create Department
        mockMvc.perform(post("/admin/departments")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"Engineering\"}"))
                .andExpect(status().isCreated());

        // Update Department
        mockMvc.perform(put("/admin/departments/{id}", deptId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"Engineering Updated\"}"))
                .andExpect(status().isOk());

        // Delete, Get All, Get By ID
        mockMvc.perform(delete("/admin/departments/{id}", deptId)).andExpect(status().isNoContent());
        mockMvc.perform(get("/admin/departments")).andExpect(status().isOk());
        mockMvc.perform(get("/admin/departments/{id}", deptId)).andExpect(status().isOk());
    }
}