package org.example.hclcapstonebe.Config;


import io.jsonwebtoken.*;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.security.Key;
import java.util.Date;

@Component
public class JwtUtil {

    @Value("${jwt.secret}")
    private String secret;

    @Value("${jwt.expiration}")
    private long expiration;

    private SecretKey getKey() {
        return Keys.hmacShaKeyFor(secret.getBytes());
    }

    public String generateToken(String email) {
        return Jwts.builder()
                .subject(email)                      // ← subject() not setSubject()
                .issuedAt(new Date())                // ← issuedAt() not setIssuedAt()
                .expiration(new Date(System.currentTimeMillis() + expiration))  // ← expiration() not setExpiration()
                .signWith(getKey())
                .compact();
    }


    public String extractEmail(String token) {
        return Jwts.parser()                          // ← parser() not parserBuilder()
                .verifyWith((SecretKey) getKey())     // ← verifyWith() not setSigningKey()
                .build()
                .parseSignedClaims(token)             // ← parseSignedClaims() not parseClaimsJws()
                .getPayload()                         // ← getPayload() not getBody()
                .getSubject();
    }

    public boolean isTokenValid(String token) {
        try {
            Jwts.parser()
                    .verifyWith((SecretKey) getKey())
                    .build()
                    .parseSignedClaims(token);
            return true;
        } catch (JwtException e) {
            return false;
        }
    }
}