package org.example.hclcapstonebe.Exception;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertAll;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

class GlobalExceptionHandlerTest {

    private final GlobalExceptionHandler handler = new GlobalExceptionHandler();

    // Single test method executing all typed exception assertions
    @Test
    void handleTypedExceptions_returnsCorrectHttpStatusAndMessage() {
        assertAll("Typed Exception Handlers",
                () -> {
                    NotFoundException ex = new NotFoundException("Resource not found");
                    ResponseEntity<Map<String, String>> res = handler.handleNotFound(ex);
                    assertEquals(HttpStatus.NOT_FOUND, res.getStatusCode());
                    assertEquals("Resource not found", res.getBody().get("error"));
                },
                () -> {
                    BadRequestException ex = new BadRequestException("Bad request payload");
                    ResponseEntity<Map<String, String>> res = handler.handleBadRequest(ex);
                    assertEquals(HttpStatus.BAD_REQUEST, res.getStatusCode());
                    assertEquals("Bad request payload", res.getBody().get("error"));
                },
                () -> {
                    ConflictException ex = new ConflictException("Email conflict");
                    ResponseEntity<Map<String, String>> res = handler.handleConflict(ex);
                    assertEquals(HttpStatus.CONFLICT, res.getStatusCode());
                    assertEquals("Email conflict", res.getBody().get("error"));
                },
                () -> {
                    AppException ex = new AppException("Unauthorized access", HttpStatus.UNAUTHORIZED);
                    ResponseEntity<Map<String, String>> res = handler.handleAppException(ex);
                    assertEquals(HttpStatus.UNAUTHORIZED, res.getStatusCode());
                    assertEquals("Unauthorized access", res.getBody().get("error"));
                    assertEquals(HttpStatus.UNAUTHORIZED, ex.getStatus());
                },
                () -> {
                    IllegalArgumentException ex = new IllegalArgumentException("Invalid UUID string: not-a-uuid");
                    ResponseEntity<Map<String, String>> res = handler.handleIllegalArgument(ex);
                    assertEquals(HttpStatus.BAD_REQUEST, res.getStatusCode());
                    assertEquals("Invalid UUID string: not-a-uuid", res.getBody().get("error"));
                }
        );
    }

    @Test
    void handleUnexpected_returns500WithGenericMessage() {
        ResponseEntity<Map<String, String>> response =
                handler.handleUnexpected(new NullPointerException("some internal detail"));

        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, response.getStatusCode());
        assertEquals("Something went wrong. Please try again later.", response.getBody().get("error"));
    }

    @Test
    void customExceptions_constructorsAndGettersWorkCorrectly() {
        InvalidFileSignatureException invalidSig = new InvalidFileSignatureException();
        assertNotNull(invalidSig.getMessage());
        assertEquals("Invalid structural file signature detected", invalidSig.getMessage());
    }
}