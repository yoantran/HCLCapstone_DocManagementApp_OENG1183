package org.example.hclcapstonebe.Config;

import org.junit.jupiter.api.Test;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.socket.config.annotation.StompEndpointRegistry;
import org.springframework.web.socket.config.annotation.StompWebSocketEndpointRegistration;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class WebSocketConfigTest {

    // Real, confirmed bug: the old extraction was
    // query.split("token=")[1].split("&")[0], a bare substring search not
    // anchored to a parameter boundary. A query like "authtoken=xxx&token=real"
    // matched the "token=" inside "authtoken=" first, returning "xxx" instead
    // of the real value named "token".
    @Test
    void extractToken_ignoresParamWhoseNameMerelyEndsInToken() {
        String query = "authtoken=xxx&token=real";

        assertEquals("real", WebSocketConfig.extractToken(query));
    }

    @Test
    void extractToken_findsTokenAsOnlyParam() {
        assertEquals("abc123", WebSocketConfig.extractToken("token=abc123"));
    }

    @Test
    void extractToken_findsTokenAmongOtherParams() {
        assertEquals("abc123", WebSocketConfig.extractToken("foo=bar&token=abc123&baz=qux"));
    }

    @Test
    void extractToken_returnsNullWhenAbsent() {
        assertNull(WebSocketConfig.extractToken("foo=bar"));
        assertNull(WebSocketConfig.extractToken(null));
    }

    @Test
    void configureMessageBroker_and_registerStompEndpoints_succeeds() {
        WebSocketConfig config = new WebSocketConfig(mock(JwtUtil.class));
        ReflectionTestUtils.setField(config, "allowedOrigins", new String[]{"http://localhost:3000"});

        MessageBrokerRegistry registry = mock(MessageBrokerRegistry.class);
        when(registry.enableSimpleBroker(any())).thenReturn(null);

        StompEndpointRegistry endpointRegistry = mock(StompEndpointRegistry.class);
        StompWebSocketEndpointRegistration registration = mock(StompWebSocketEndpointRegistration.class);
        when(endpointRegistry.addEndpoint("/ws")).thenReturn(registration);
        when(registration.setAllowedOrigins(any())).thenReturn(registration);

        assertDoesNotThrow(() -> {
            config.configureMessageBroker(registry);
            config.registerStompEndpoints(endpointRegistry);
        });

        verify(registry).enableSimpleBroker("/topic", "/queue");
        verify(registry).setApplicationDestinationPrefixes("/app");
        verify(endpointRegistry).addEndpoint("/ws");
    }
}
