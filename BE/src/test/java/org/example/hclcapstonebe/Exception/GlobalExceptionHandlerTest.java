package org.example.hclcapstonebe.Exception;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GlobalExceptionHandlerTest {

    private final GlobalExceptionHandler handler = new GlobalExceptionHandler();

    // Real, confirmed bug: AdminController calls UUID.fromString() directly
    // on raw @PathVariable strings (deleteUser, getUserById, deleteDepartment).
    // A malformed UUID throws IllegalArgumentException, which had no handler
    // here -- Spring's default fell through to a 500 instead of a 400.
    @Test
    void handleIllegalArgument_returns400() {
        ResponseEntity<Map<String, String>> response =
                handler.handleIllegalArgument(new IllegalArgumentException("Invalid UUID string: not-a-uuid"));

        assertEquals(HttpStatus.BAD_REQUEST, response.getStatusCode());
    }

    // Real, confirmed gap: this advice had no catch-all handler (removed in
    // an earlier commit, replaced only with typed handlers) -- any exception
    // outside those types (e.g. a NullPointerException) fell through to
    // Spring Boot's default error page instead of this app's
    // {"error": ...} JSON contract, and the raw exception message was never
    // exposed to the client either way.
    @Test
    void handleUnexpected_returns500WithGenericMessage() {
        ResponseEntity<Map<String, String>> response =
                handler.handleUnexpected(new NullPointerException("some internal detail"));

        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, response.getStatusCode());
        assertEquals("Something went wrong. Please try again later.", response.getBody().get("error"));
    }
}
