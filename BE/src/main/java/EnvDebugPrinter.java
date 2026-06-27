package org.example.hclcapstonebe.Config;

import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
public class EnvDebugPrinter {

    private final Environment env;

    @PostConstruct
    public void printEnv() {
        System.out.println("\n===== SERVICE-TOKEN CONFIG DEBUG =====");
        System.out.println("client-id          = " + env.getProperty("app.service-token.client-id"));
        String hash = env.getProperty("app.service-token.client-secret-hash");
        System.out.println("client-secret-hash = " +
                (hash == null ? "null"
                        : hash.substring(0, Math.min(12, hash.length())) + "...(" + hash.length() + " chars)"));
        System.out.println("hash is placeholder? = " + (hash != null && hash.contains("REPLACE")));
        System.out.println("======================================\n");
    }
}
