package org.example.hclcapstonebe.Controller;

import org.example.hclcapstonebe.DTO.Response.DocumentResponse;
import org.example.hclcapstonebe.DTO.Response.RedactedPreviewResponse;
import org.example.hclcapstonebe.Service.DocumentService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.List;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@ExtendWith(MockitoExtension.class)
class DocumentControllerTest {

    @Mock private DocumentService documentService;
    @InjectMocks private DocumentController documentController;

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

        mockMvc = MockMvcBuilders.standaloneSetup(documentController)
                .setCustomArgumentResolvers(principalResolver)
                .build();
    }

    @Test
    void documentOperations_executeSuccessfully() throws Exception {
        UUID docId = UUID.randomUUID();
        when(documentService.uploadOne(any(), any(), any(), any())).thenReturn(new DocumentResponse());
        when(documentService.uploadMany(any(), any(), any(), any())).thenReturn(List.of());
        when(documentService.getMyDocuments(any())).thenReturn(List.of());
        when(documentService.getMyDocumentById(any(), any())).thenReturn(new DocumentResponse());
        when(documentService.getDepartmentDocuments(any())).thenReturn(List.of());
        when(documentService.getDepartmentDocumentById(any(), any())).thenReturn(new DocumentResponse());
        when(documentService.getRedactedPreviewStatus(any(), any(), anyBoolean())).thenReturn(new RedactedPreviewResponse());

        MockMultipartFile file = new MockMultipartFile("file", "doc.pdf", "application/pdf", "data".getBytes());
        MockMultipartFile files = new MockMultipartFile("files", "doc.pdf", "application/pdf", "data".getBytes());

        // Upload Single
        mockMvc.perform(multipart("/documents/upload")
                        .file(file)
                        .param("type", "CONTRACT"))
                .andExpect(status().isCreated());

        // Upload Batch
        mockMvc.perform(multipart("/documents/upload/batch")
                        .file(files)
                        .param("type", "PAY_SLIP"))
                .andExpect(status().isCreated());

        // Get Mine & Get Mine By ID
        mockMvc.perform(get("/documents/mine")).andExpect(status().isOk());
        mockMvc.perform(get("/documents/mine/{id}", docId)).andExpect(status().isOk());

        // Get Department & Get Department By ID
        mockMvc.perform(get("/documents/department")).andExpect(status().isOk());
        mockMvc.perform(get("/documents/department/{id}", docId)).andExpect(status().isOk());

        // Redacted Preview
        mockMvc.perform(get("/documents/{id}/redacted-preview", docId)).andExpect(status().isOk());

        // Delete
        mockMvc.perform(delete("/documents/{id}", docId)).andExpect(status().isNoContent());
    }
}