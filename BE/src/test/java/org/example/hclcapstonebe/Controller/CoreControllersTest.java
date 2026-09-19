package org.example.hclcapstonebe.Controller;

import org.example.hclcapstonebe.Audit.AuditLogStore;
import org.example.hclcapstonebe.DTO.Request.LoginRequest;
import org.example.hclcapstonebe.DTO.Response.AuthResponse;
import org.example.hclcapstonebe.DTO.Response.NotificationResponse;
import org.example.hclcapstonebe.DTO.Response.UserProfileResponse;
import org.example.hclcapstonebe.Service.AuthService;
import org.example.hclcapstonebe.Service.NotificationService;
import org.example.hclcapstonebe.Service.UserService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.List;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@ExtendWith(MockitoExtension.class)
class CoreControllersTest {

    @Mock private AuthService authService;
    @Mock private UserService userService;
    @Mock private NotificationService notificationService;
    @Mock private AuditLogStore auditLogStore;

    @InjectMocks private AuthController authController;
    @InjectMocks private UserController userController;
    @InjectMocks private NotificationController notificationController;
    @InjectMocks private AdminAuditLogController auditLogController;

    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        org.springframework.web.method.support.HandlerMethodArgumentResolver principalResolver =
                new org.springframework.web.method.support.HandlerMethodArgumentResolver() {
                    @Override
                    public boolean supportsParameter(org.springframework.core.MethodParameter parameter) {
                        return parameter.getParameterType().isAssignableFrom(
                                org.springframework.security.core.userdetails.UserDetails.class);
                    }

                    @Override
                    public Object resolveArgument(org.springframework.core.MethodParameter parameter,
                                                  org.springframework.web.method.support.ModelAndViewContainer mavContainer,
                                                  org.springframework.web.context.request.NativeWebRequest webRequest,
                                                  org.springframework.web.bind.support.WebDataBinderFactory binderFactory) {
                        return new org.springframework.security.core.userdetails.User(
                                "user@hcl.com", "password", java.util.List.of());
                    }
                };

        mockMvc = MockMvcBuilders.standaloneSetup(
                        authController, userController, notificationController, auditLogController)
                .setCustomArgumentResolvers(principalResolver)
                .build();
    }

    @Test
    void authAndUserEndpoints_executeSuccessfully() throws Exception {
        when(authService.login(any())).thenReturn(new AuthResponse("id", "token", "STAFF", "admin@hcl.com", "Admin", "dept-1"));
        when(userService.getProfile(any())).thenReturn(new UserProfileResponse());
        when(userService.updateProfile(any(), any(), any())).thenReturn(new UserProfileResponse());

        // Auth: Login & Logout
        mockMvc.perform(post("/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"admin@hcl.com\",\"password\":\"pass\"}"))
                .andExpect(status().isOk());

        mockMvc.perform(post("/auth/logout")).andExpect(status().isOk());

        // User Profile GET & PUT
        mockMvc.perform(get("/users/me")).andExpect(status().isOk());

        MockMultipartFile avatar = new MockMultipartFile("avatar", "pic.png", "image/png", "bytes".getBytes());
        mockMvc.perform(multipart("/users/me")
                        .file(avatar)
                        .param("name", "New Name")
                        .param("phoneNumber", "0901234567")
                        .with(request -> { request.setMethod("PUT"); return request; }))
                .andExpect(status().isOk());
    }

    @Test
    void notificationAndAuditLogEndpoints_executeSuccessfully() throws Exception {
        UUID notifId = UUID.randomUUID();
        when(notificationService.getMyNotifications(any())).thenReturn(List.of());
        when(notificationService.markAsRead(eq(notifId), any())).thenReturn(new NotificationResponse());
        when(auditLogStore.query(any(), any(), any(), any(), anyInt())).thenReturn(List.of());

        // Notification GET & PATCH
        mockMvc.perform(get("/notifications")).andExpect(status().isOk());
        mockMvc.perform(patch("/notifications/{id}/read", notifId)).andExpect(status().isOk());

        // Audit Log GET, STATS, DELETE
        mockMvc.perform(get("/admin/audit-logs").param("limit", "10")).andExpect(status().isOk());
        mockMvc.perform(get("/admin/audit-logs/stats")).andExpect(status().isOk());
        mockMvc.perform(delete("/admin/audit-logs")).andExpect(status().isNoContent());
    }
}