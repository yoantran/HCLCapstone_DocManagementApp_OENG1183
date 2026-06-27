package org.example.hclcapstonebe.DTO.Request;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "Credentials for a service client requesting a short-lived service token")
public record ServiceTokenRequest(
        @Schema(description = "Service client identifier", example = "malware-scan-service")
        String clientId,
        @Schema(description = "Service client secret (shared out-of-band)", example = "s3cr3t-raw-value")
        String clientSecret
) {}
