package org.example.hclcapstonebe.Config;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

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
}
