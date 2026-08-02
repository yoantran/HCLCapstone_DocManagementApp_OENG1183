package org.example.hclcapstonebe.Audit;

import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.reflect.MethodSignature;
import org.example.hclcapstonebe.Entities.User;
import org.example.hclcapstonebe.Repository.DepartmentRepository;
import org.example.hclcapstonebe.Repository.DocumentRepository;
import org.example.hclcapstonebe.Repository.UserRepository;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;
import org.springframework.web.multipart.MultipartFile;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Parameter;
import java.time.LocalDateTime;
import java.util.UUID;

@Aspect
@Component
@RequiredArgsConstructor
public class AuditAspect {

    private final AuditLogStore store;
    private final UserRepository userRepository;
    private final DocumentRepository documentRepository;
    private final DepartmentRepository departmentRepository;

    @Around("within(org.example.hclcapstonebe.Controller..*)")
    public Object audit(ProceedingJoinPoint pjp) throws Throwable {
        long start = System.currentTimeMillis();
        HttpServletRequest req = currentRequest();

        MethodSignature signature = (MethodSignature) pjp.getSignature();
        Method method = signature.getMethod();

        AuditAction annotation = method.getAnnotation(AuditAction.class);

        String action;

        if (annotation != null) {
            action = buildAction(annotation.value(), method, pjp.getArgs());
        } else {
            action = signature.getDeclaringType().getSimpleName()
                    + "." + signature.getName();
        }

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
        String name = "anonymous";
        String email = "anonymous";
        String role = "NONE";

        if (auth != null && auth.isAuthenticated()
                && !"anonymousUser".equals(String.valueOf(auth.getPrincipal()))) {
            email = auth.getName();
            role = auth.getAuthorities().stream()
                    .findFirst().map(Object::toString).orElse("NONE");
            User user = userRepository.findByEmailAndIsDeletedFalse(email).get();
            userId = user.getId().toString();
            name = user.getName();
        }

        store.add(AuditEntry.builder()
                .timestamp(LocalDateTime.now())
                .userId(userId)
                .name(name)
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

    // Helpers
    private String buildAction(String template, Method method, Object[] args) {
        String action = template;
        Parameter[] parameters = method.getParameters();

        for (int i = 0; i < parameters.length; i++) {
            Object arg = args[i];

            // handle placeholders like {id}, {userId}, ...
            String placeholder = "{" + parameters[i].getName() + "}";
            if (action.contains(placeholder)) {
                action = action.replace(
                        placeholder,
                        formatArgument(parameters[i].getName(), arg)
                );
            }
            // handle placeholders like {req.name}
            if (arg != null &&
                    arg.getClass().getPackageName().startsWith("org.example.hclcapstonebe.DTO")) {

                for (Field field : arg.getClass().getDeclaredFields()) {
                    try {
                        field.setAccessible(true);
                        String nestedPlaceholder =
                                "{" + parameters[i].getName() + "." + field.getName() + "}";

                        if (action.contains(nestedPlaceholder)) {
                            Object value = field.get(arg);
                            action = action.replace(
                                    nestedPlaceholder,
                                    value == null ? "null" : value.toString()
                            );
                        }
                    } catch (IllegalAccessException ignored) {}
                }
            }
        }
        return action;
    }

    private String formatArgument(String parameterName, Object arg) {
        switch (arg) {
            case null -> {
                return "null";
            }
            case MultipartFile file -> {
                return file.getOriginalFilename();
            }
            case UUID uuid -> {
                return resolveEntityName(parameterName, uuid);
            }
            case String id -> {
                try {
                    return resolveEntityName(parameterName, UUID.fromString(id));
                } catch (IllegalArgumentException ignored) {
                    return id;
                }
            }
            default -> {}
        }
        return String.valueOf(arg);
    }

    private String resolveEntityName(String parameterName, UUID uuid) {
        return switch (parameterName) {
            case "documentId" ->
                    documentRepository.findById(uuid)
                            .map(doc -> "%s [%s]".formatted(doc.getName(), doc.getId()))
                            .orElse(uuid.toString());
            case "userId" ->
                    userRepository.findById(uuid)
                            .map(user -> "%s [%s]".formatted(user.getName(), user.getId()))
                            .orElse(uuid.toString());
            case "departmentId" ->
                    departmentRepository.findById(uuid)
                            .map(dept -> "%s [%s]".formatted(dept.getName(), dept.getId()))
                            .orElse(uuid.toString());

            default -> uuid.toString();
        };
    }
}