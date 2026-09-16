package org.example.hclcapstonebe.Audit;

import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.reflect.MethodSignature;
import org.example.hclcapstonebe.Exception.AppException;
import org.example.hclcapstonebe.Repository.DepartmentRepository;
import org.example.hclcapstonebe.Repository.DocumentRepository;
import org.example.hclcapstonebe.Repository.UserRepository;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.HttpStatus;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AuditAspectTest {

    private final AuditLogStore store = mock(AuditLogStore.class);
    private final AuditAspect aspect = new AuditAspect(
            store, mock(UserRepository.class), mock(DocumentRepository.class), mock(DepartmentRepository.class));

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

    // Real, confirmed bug: a wrong-password login throws AppException(401),
    // which GlobalExceptionHandler correctly turns into a 401 response for
    // the client -- but the aspect's catch block hardcoded status 500 for
    // every thrown exception, so the audit trail recorded a failed login
    // (and any other typed 4xx exception) as a server error instead.
    @Test
    void appException_isRecordedWithItsOwnStatus_notHardcoded500() throws Throwable {
        ProceedingJoinPoint pjp = pjpThrowing(new AppException("Invalid credentials", HttpStatus.UNAUTHORIZED));

        assertThrows(AppException.class, () -> aspect.audit(pjp));

        ArgumentCaptor<AuditEntry> captor = ArgumentCaptor.forClass(AuditEntry.class);
        verify(store).add(captor.capture());
        assertEquals(401, captor.getValue().getStatus());
    }

    @Test
    void unmappedException_stillRecordsAs500() throws Throwable {
        ProceedingJoinPoint pjp = pjpThrowing(new RuntimeException("boom"));

        assertThrows(RuntimeException.class, () -> aspect.audit(pjp));

        ArgumentCaptor<AuditEntry> captor = ArgumentCaptor.forClass(AuditEntry.class);
        verify(store).add(captor.capture());
        assertEquals(500, captor.getValue().getStatus());
    }
}
