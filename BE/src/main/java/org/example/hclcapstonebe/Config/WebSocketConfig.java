package org.example.hclcapstonebe.Config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.web.socket.config.annotation.*;
import org.springframework.http.server.ServerHttpRequest;
import org.springframework.web.socket.WebSocketHandler;
import lombok.RequiredArgsConstructor;

import java.security.Principal;
import java.util.Map;

@Configuration
@EnableWebSocketMessageBroker
@RequiredArgsConstructor
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {
    private final JwtUtil jwtUtil;

    @Value("${app.cors.allowed-origins}")
    private String[] allowedOrigins;

    // Anchors on a real "token" query param name instead of a bare substring
    // search, and doesn't blindly trust it -- validate before extracting.
    static String extractToken(String query) {
        if (query == null) {
            return null;
        }
        for (String pair : query.split("&")) {
            int idx = pair.indexOf('=');
            String key = idx >= 0 ? pair.substring(0, idx) : pair;
            if (key.equals("token")) {
                return idx >= 0 ? pair.substring(idx + 1) : "";
            }
        }
        return null;
    }

    @Override
    public void configureMessageBroker(MessageBrokerRegistry registry) {
        registry.enableSimpleBroker("/topic", "/queue");
        registry.setApplicationDestinationPrefixes("/app");
        registry.setUserDestinationPrefix("/user");
    }

    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        registry.addEndpoint("/ws")
                .setAllowedOrigins(allowedOrigins)
                .setHandshakeHandler(new org.springframework.web.socket.server.support.DefaultHandshakeHandler() {
                    @Override
                    protected Principal determineUser(ServerHttpRequest request,
                            WebSocketHandler wsHandler, Map<String, Object> attributes) {
                        String token = extractToken(request.getURI().getQuery());

                        if (token != null && jwtUtil.isTokenValid(token)) {
                            String email = jwtUtil.extractEmail(token);
                            return () -> email;
                        }
                        return null;
                    }
                });
    }

}
