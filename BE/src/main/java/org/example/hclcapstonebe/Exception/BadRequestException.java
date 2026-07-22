package org.example.hclcapstonebe.Exception;

public class BadRequestException extends RuntimeException {
    public BadRequestException(String message) { super(message); }
}