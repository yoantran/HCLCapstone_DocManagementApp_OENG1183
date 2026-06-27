package org.example.hclcapstonebe.Controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.ExampleObject;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.example.hclcapstonebe.Config.ServiceCredentialStore;
import org.example.hclcapstonebe.Config.ServiceTokenProvider;
import org.example.hclcapstonebe.DTO.Request.ServiceTokenRequest;
import org.example.hclcapstonebe.DTO.Response.ServiceTokenResponse;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/auth/service-token")
@RequiredArgsConstructor
@Tag(name = "Service Auth", description = "Machine-to-machine token issuance for trusted services (e.g. malware-scan).")
public class ServiceTokenController {

    private final ServiceCredentialStore credentialStore;
    private final ServiceTokenProvider tokenProvider;

    @Operation(
            summary = "Issue a short-lived service token",
            description = """
                Exchanges a service client_id + client_secret for a short-lived JWT service token.
                The returned token must be sent in the `X-Service-Token` header on calls to the
                document upload endpoints. Tokens expire (default 5 minutes); request a new one
                when the current token nears expiry.
                
                This endpoint is for trusted backend services only, NOT for end users or browsers.
                """
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "Service token issued",
                    content = @Content(
                            mediaType = "application/json",
                            examples = @ExampleObject(value = """
                {
                    "accessToken": "eyJhbGciOiJIUzI1NiJ9...",
                    "expiresIn": 300,
                    "tokenType": "Bearer"
                }
            """))
            ),
            @ApiResponse(responseCode = "401", description = "Invalid client_id or client_secret")
    })
    @PostMapping
    public ResponseEntity<ServiceTokenResponse> issue(@RequestBody ServiceTokenRequest request) {
        if (!credentialStore.verify(request.clientId(), request.clientSecret())) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        String token = tokenProvider.generate(request.clientId());
        return ResponseEntity.ok(new ServiceTokenResponse(
                token, tokenProvider.getExpirySeconds(), "Bearer"));
    }
}