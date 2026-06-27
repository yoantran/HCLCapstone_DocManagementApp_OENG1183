package org.example.hclcapstonebe.Config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

@Component
public class ServiceCredentialStore {

    @Value("${app.service-token.client-id}")
    private String clientId;

    /** BCrypt hash of the client secret, NOT the raw value. */
    @Value("${app.service-token.client-secret-hash}")
    private String clientSecretHash;

    private final PasswordEncoder passwordEncoder;

    public ServiceCredentialStore(PasswordEncoder passwordEncoder) {
        this.passwordEncoder = passwordEncoder;
    }

    public boolean verify(String id, String rawSecret) {
        if (id == null || rawSecret == null) return false;
        return clientId.equals(id) && passwordEncoder.matches(rawSecret, clientSecretHash);
    }
}