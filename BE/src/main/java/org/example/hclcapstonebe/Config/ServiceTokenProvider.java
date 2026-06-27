package org.example.hclcapstonebe.Config;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;

@Component
public class ServiceTokenProvider {

    @Value("${app.service-token.secret}")
    private String secret;

    @Value("${app.service-token.expiry-seconds:300}")
    private long expirySeconds;

    private SecretKey key() {
        return Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }

    /** Self-test: prove generate + verify agree within this running instance. */
    @PostConstruct
    void selfTest() {
        try {
            String t = generate("self-test");
            boolean ok = isValidScanToken(t);
            System.out.println("[ServiceTokenProvider] secretLength=" + secret.length()
                    + " bytes, immediate self-verify=" + ok);
        } catch (Exception e) {
            System.out.println("[ServiceTokenProvider] SELF-TEST FAILED: "
                    + e.getClass().getSimpleName() + " - " + e.getMessage());
        }
    }

    public String generate(String clientId) {
        long now = System.currentTimeMillis();
        return Jwts.builder()
                .subject(clientId)
                .claim("type", "SERVICE")
                .claim("role", "SERVICE_SCAN")
                .issuedAt(new Date(now))
                .expiration(new Date(now + expirySeconds * 1000))
                .signWith(key())
                .compact();
    }

    /** Returns true only if the token is a valid, unexpired SERVICE_SCAN token. */
    public boolean isValidScanToken(String token) {
        try {
            Claims claims = Jwts.parser()
                    .verifyWith(key())
                    .build()
                    .parseSignedClaims(token)
                    .getPayload();
            boolean ok = "SERVICE".equals(claims.get("type"))
                    && "SERVICE_SCAN".equals(claims.get("role"));
            System.out.println("[scan-token] valid=" + ok
                    + " sub=" + claims.getSubject()
                    + " exp=" + claims.getExpiration());
            return ok;
        } catch (Exception e) {
            // No longer silent — shows the REAL reason
            System.out.println("[scan-token] REJECTED: "
                    + e.getClass().getSimpleName() + " - " + e.getMessage());
            return false;
        }
    }

    public long getExpirySeconds() {
        return expirySeconds;
    }
}