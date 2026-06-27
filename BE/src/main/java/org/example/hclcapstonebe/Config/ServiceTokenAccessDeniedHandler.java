package org.example.hclcapstonebe.Config;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.web.access.AccessDeniedHandler;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.Map;

@Component
public class ServiceTokenAccessDeniedHandler implements AccessDeniedHandler {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public void handle(HttpServletRequest request,
                       HttpServletResponse response,
                       AccessDeniedException ex) throws IOException {

        String path = request.getRequestURI();
        boolean isUploadEndpoint = "POST".equalsIgnoreCase(request.getMethod())
                && (path.equals("/documents/upload") || path.equals("/documents/upload/batch"));

        String message;
        if (isUploadEndpoint) {
            String token = request.getHeader("X-Service-Token");
            message = (token == null || token.isBlank())
                    ? "Missing X-Service-Token. Authenticate as the malware-scan service via POST /auth/service-token to obtain one."
                    : "Service token invalid or expired. Please login as the malware-scan service (POST /auth/service-token) to get a new service token.";
        } else {
            message = "Access denied: insufficient permissions.";
        }

        response.setStatus(HttpStatus.FORBIDDEN.value());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        objectMapper.writeValue(response.getWriter(), Map.of(
                "status", 403,
                "error", "Forbidden",
                "message", message,
                "path", path,
                "timestamp", LocalDateTime.now().toString()
        ));
    }
}