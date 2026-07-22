package org.example.hclcapstonebe.Audit;

import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.example.hclcapstonebe.Repository.UserRepository;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.time.LocalDateTime;

@Aspect
@Component
@RequiredArgsConstructor
public class AuditAspect {

    private final AuditLogStore store;
    private final UserRepository userRepository;

    @Around("within(org.example.hclcapstonebe.Controller..*)")
    public Object audit(ProceedingJoinPoint pjp) throws Throwable {
        long start = System.currentTimeMillis();
        HttpServletRequest req = currentRequest();

        String action = pjp.getSignature().getDeclaringType().getSimpleName()
                + "." + pjp.getSignature().getName();

        try {
            Object result = pjp.proceed();
            record(req, action, start, statusOf(result), null);
            return result;
        } catch (Throwable ex) {
            record(req, action, start, 500, ex.getClass().getSimpleName() + ": " + ex.getMessage());
            throw ex;
        }
    }

    private void record(HttpServletRequest req, String action, long start,
                        int status, String error) {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();

        String userId = "anonymous";
        String email = "anonymous";
        String role = "NONE";

        if (auth != null && auth.isAuthenticated()
                && !"anonymousUser".equals(String.valueOf(auth.getPrincipal()))) {
            email = auth.getName();
            role = auth.getAuthorities().stream()
                    .findFirst().map(Object::toString).orElse("NONE");
            userId = resolveUserId(auth);
        }

        store.add(AuditEntry.builder()
                .timestamp(LocalDateTime.now())
                .userId(userId)
                .email(email)
                .role(role)
                .method(req != null ? req.getMethod() : "N/A")
                .path(req != null ? req.getRequestURI() : "N/A")
                .action(action)
                .status(status)
                .durationMs(System.currentTimeMillis() - start)
                .clientIp(req != null ? clientIp(req) : "N/A")
                .error(error)
                .build());
    }

    /**
     * Adapt to your UserDetails implementation. If your principal is a custom
     * class holding the UUID, cast and pull it here instead.
     */
    private String resolveUserId(Authentication auth) {
        String email = auth.getName();

        return userRepository.findByEmailAndIsDeletedFalse(email)
                .map(user -> user.getId().toString())
                .orElse(email);
    }

    private int statusOf(Object result) {
        if (result instanceof org.springframework.http.ResponseEntity<?> re) {
            return re.getStatusCode().value();
        }
        return 200;
    }

    private String clientIp(HttpServletRequest req) {
        String forwarded = req.getHeader("X-Forwarded-For");
        return (forwarded != null && !forwarded.isBlank())
                ? forwarded.split(",")[0].trim()
                : req.getRemoteAddr();
    }

    private HttpServletRequest currentRequest() {
        var attrs = RequestContextHolder.getRequestAttributes();
        return (attrs instanceof ServletRequestAttributes sra) ? sra.getRequest() : null;
    }
}