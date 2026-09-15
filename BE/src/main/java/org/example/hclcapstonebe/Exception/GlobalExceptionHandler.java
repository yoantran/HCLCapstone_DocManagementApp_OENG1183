package org.example.hclcapstonebe.Exception;


import lombok.extern.slf4j.Slf4j;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(NotFoundException.class)
    public ResponseEntity<Map<String, String>> handleNotFound(NotFoundException ex) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of("error", ex.getMessage()));
    }

    @ExceptionHandler(BadRequestException.class)
    public ResponseEntity<Map<String, String>> handleBadRequest(BadRequestException ex) {
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of("error", ex.getMessage()));
    }

    @ExceptionHandler(ConflictException.class)
    public ResponseEntity<Map<String, String>> handleConflict(ConflictException ex) {
        return ResponseEntity.status(HttpStatus.CONFLICT).body(Map.of("error", ex.getMessage()));
    }

    @ExceptionHandler(AppException.class)
    public ResponseEntity<Map<String, String>> handleAppException(AppException ex) {
        return ResponseEntity.status(ex.getStatus()).body(Map.of("error", ex.getMessage()));
    }

    // Catches malformed path-variable parsing (e.g. UUID.fromString on an
    // invalid path segment), which previously 500'd instead of 400ing.
    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<Map<String, String>> handleIllegalArgument(IllegalArgumentException ex) {
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of("error", ex.getMessage()));
    }

    // Real, confirmed gap: this advice had no catch-all, so any exception
    // outside the typed handlers above (NPE, a DB access error, etc.) fell
    // through to Spring Boot's default error page instead of this app's
    // {"error": ...} contract. The exception is logged in full server-side;
    // the client only gets a generic message, never the raw exception text.
    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, String>> handleUnexpected(Exception ex) {
        log.error("Unhandled exception", ex);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(Map.of("error", "Something went wrong. Please try again later."));
    }
}