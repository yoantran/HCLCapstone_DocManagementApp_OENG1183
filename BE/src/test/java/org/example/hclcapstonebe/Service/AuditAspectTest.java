package org.example.hclcapstonebe.Service;

import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.reflect.MethodSignature;
import org.example.hclcapstonebe.Audit.AuditAction;
import org.example.hclcapstonebe.Audit.AuditAspect;
import org.example.hclcapstonebe.Audit.AuditEntry;
import org.example.hclcapstonebe.Audit.AuditLogStore;
import org.example.hclcapstonebe.DTO.Request.CreateUserRequest;
import org.example.hclcapstonebe.Entities.Document;
import org.example.hclcapstonebe.Entities.User;
import org.example.hclcapstonebe.Exception.AppException;
import org.example.hclcapstonebe.Exception.BadRequestException;
import org.example.hclcapstonebe.Exception.ConflictException;
import org.example.hclcapstonebe.Exception.NotFoundException;
import org.example.hclcapstonebe.Repository.DepartmentRepository;
import org.example.hclcapstonebe.Repository.DocumentRepository;
import org.example.hclcapstonebe.Repository.UserRepository;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.lang.reflect.Method;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class AuditAspectTest {

    private AuditLogStore store;
    private UserRepository userRepository;
    private DocumentRepository documentRepository;
    private DepartmentRepository departmentRepository;
    private AuditAspect aspect;

    @BeforeEach
    void setUp() {
        store = mock(AuditLogStore.class);
        userRepository = mock(UserRepository.class);
        documentRepository = mock(DocumentRepository.class);
        departmentRepository = mock(DepartmentRepository.class);

        aspect = new AuditAspect(store, userRepository, documentRepository, departmentRepository);

        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/api/v1/test");
        request.setRemoteAddr("127.0.0.1");
        request.addHeader("X-Forwarded-For", "192.168.1.1, 10.0.0.1");
        RequestContextHolder.setRequestAttributes(new ServletRequestAttributes(request));
    }

    @AfterEach
    void tearDown() {
        RequestContextHolder.resetRequestAttributes();
        SecurityContextHolder.clearContext();
    }

    @AuditAction("Uploaded {file} for {documentId} by {req.email}")
    public void dummyAnnotatedMethod(MockMultipartFile file, UUID documentId, CreateUserRequest req) {}

    @Test
    void audit_successfulExecution_withAuthenticatedUserAndAnnotation() throws Throwable {
        UUID docId = UUID.randomUUID();
        UUID userId = UUID.randomUUID();

        Method method = this.getClass().getMethod("dummyAnnotatedMethod", MockMultipartFile.class, UUID.class, CreateUserRequest.class);
        MockMultipartFile file = new MockMultipartFile("file", "test.pdf", "application/pdf", new byte[0]);
        CreateUserRequest req = new CreateUserRequest();
        req.setEmail("target@hcl.com");

        ProceedingJoinPoint pjp = mock(ProceedingJoinPoint.class);
        MethodSignature signature = mock(MethodSignature.class);
        when(pjp.getSignature()).thenReturn(signature);
        when(signature.getMethod()).thenReturn(method);
        when(pjp.getArgs()).thenReturn(new Object[]{file, docId, req});
        when(pjp.proceed()).thenReturn(ResponseEntity.ok("Done"));

        UsernamePasswordAuthenticationToken auth =
                new UsernamePasswordAuthenticationToken("user@hcl.com", "pass", List.of(() -> "ROLE_STAFF"));
        SecurityContextHolder.getContext().setAuthentication(auth);

        User user = new User();
        user.setId(userId);
        user.setName("John Staff");
        when(userRepository.findByEmailAndIsDeletedFalse("user@hcl.com")).thenReturn(Optional.of(user));

        Document doc = new Document();
        doc.setId(docId);
        doc.setName("test.pdf");
        when(documentRepository.findById(docId)).thenReturn(Optional.of(doc));

        Object result = aspect.audit(pjp);

        assertNotNull(result);
        ArgumentCaptor<AuditEntry> captor = ArgumentCaptor.forClass(AuditEntry.class);
        verify(store).add(captor.capture());

        AuditEntry entry = captor.getValue();
        assertEquals(200, entry.getStatus());
        assertEquals("192.168.1.1", entry.getClientIp());
        assertEquals("John Staff", entry.getName());
        assertTrue(entry.getAction().contains("Uploaded test.pdf"));
    }

    @Test
    void appException_isRecordedWithItsOwnStatus_notHardcoded500() throws Throwable {
        ProceedingJoinPoint pjp = pjpThrowing(new AppException("Invalid credentials", HttpStatus.UNAUTHORIZED));

        assertThrows(AppException.class, () -> aspect.audit(pjp));

        ArgumentCaptor<AuditEntry> captor = ArgumentCaptor.forClass(AuditEntry.class);
        verify(store).add(captor.capture());
        assertEquals(401, captor.getValue().getStatus());
    }

    @Test
    void statusOfException_mapsCustomExceptionsCorrectly() throws Throwable {
        assertExceptionStatus(new NotFoundException("Missing"), 404);
        assertExceptionStatus(new BadRequestException("Bad"), 400);
        assertExceptionStatus(new ConflictException("Conflict"), 409);
        assertExceptionStatus(new IllegalArgumentException("Arg"), 400);
    }

    @Test
    void unmappedException_stillRecordsAs500() throws Throwable {
        ProceedingJoinPoint pjp = pjpThrowing(new RuntimeException("boom"));

        assertThrows(RuntimeException.class, () -> aspect.audit(pjp));

        ArgumentCaptor<AuditEntry> captor = ArgumentCaptor.forClass(AuditEntry.class);
        verify(store).add(captor.capture());
        assertEquals(500, captor.getValue().getStatus());
    }

    private void assertExceptionStatus(Throwable ex, int expectedStatus) throws Throwable {
        ProceedingJoinPoint pjp = pjpThrowing(ex);
        assertThrows(ex.getClass(), () -> aspect.audit(pjp));

        ArgumentCaptor<AuditEntry> captor = ArgumentCaptor.forClass(AuditEntry.class);
        verify(store, atLeastOnce()).add(captor.capture());
        assertEquals(expectedStatus, captor.getValue().getStatus());
    }

    private ProceedingJoinPoint pjpThrowing(Throwable toThrow) throws Throwable {
        ProceedingJoinPoint pjp = mock(ProceedingJoinPoint.class);
        MethodSignature signature = mock(MethodSignature.class);
        when(pjp.getSignature()).thenReturn(signature);
        when(signature.getMethod()).thenReturn(Object.class.getMethod("toString"));
        when(signature.getDeclaringType()).thenReturn((Class) Object.class);
        when(signature.getName()).thenReturn("toString");
        when(pjp.getArgs()).thenReturn(new Object[0]);
        when(pjp.proceed()).thenThrow(toThrow);
        return pjp;
    }
}