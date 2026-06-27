package org.example.hclcapstonebe.DTO.Response;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "Short-lived service access token response")
public record ServiceTokenResponse(
        @Schema(description = "The signed service JWT to send as X-Service-Token")
        String accessToken,
        @Schema(description = "Token lifetime in seconds", example = "300")
        long expiresIn,
        @Schema(description = "Token type", example = "Bearer")
        String tokenType
) {}