package org.example.hclcapstonebe.Exception;

public class InvalidFileSignatureException extends BadRequestException {
    public InvalidFileSignatureException() {
        super("Invalid structural file signature detected");
    }
}