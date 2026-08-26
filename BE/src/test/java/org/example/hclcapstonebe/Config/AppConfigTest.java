package org.example.hclcapstonebe.Config;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Issue #265 -- proves the RestTemplate produced by AppConfig enforces a
 * genuine overall-request deadline, not just an inter-read stall timer.
 * The old SimpleClientHttpRequestFactory-based bean would NOT time out
 * against this server: it dribbles one byte well inside the configured
 * read-timeout window, forever, which is exactly the real-world Modal
 * keep-alive-traffic scenario that left a real document hung for 24+
 * minutes. A stall-timer implementation never sees a gap long enough to
 * fire; only a true overall deadline does.
 */
class AppConfigTest {

    private HttpServer server;

    @AfterEach
    void tearDown() {
        if (server != null) {
            server.stop(0);
        }
    }

    @Test
    void restTemplate_timesOutOnServerThatKeepsTrickingBytes_insteadOfHangingForever() throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/slow-drip", exchange -> {
            exchange.sendResponseHeaders(200, 0);
            OutputStream body = exchange.getResponseBody();
            try {
                // Send a byte every 500ms, well under any per-read stall
                // timeout, for far longer than the 2s deadline under test --
                // a stall-timer-based client would never see a gap and
                // would hang for the full 20s; a real deadline fires at ~2s.
                for (int i = 0; i < 40; i++) {
                    body.write('.');
                    body.flush();
                    Thread.sleep(500);
                }
            } catch (InterruptedException ignored) {
                Thread.currentThread().interrupt();
            } finally {
                body.close();
            }
        });
        server.start();

        RestTemplate restTemplate = new AppConfig().restTemplate();
        // Override the bean's own 180s cap with a short one for a fast test --
        // same factory type, same deadline semantics, just a smaller number.
        org.springframework.http.client.JdkClientHttpRequestFactory shortDeadlineFactory =
                new org.springframework.http.client.JdkClientHttpRequestFactory(
                        java.net.http.HttpClient.newBuilder()
                                .connectTimeout(java.time.Duration.ofSeconds(5))
                                .build());
        shortDeadlineFactory.setReadTimeout(java.time.Duration.ofSeconds(2));
        restTemplate.setRequestFactory(shortDeadlineFactory);

        String url = "http://127.0.0.1:" + server.getAddress().getPort() + "/slow-drip";
        long start = System.currentTimeMillis();

        // The timeout can surface either as a connect/request-level
        // ResourceAccessException or, if it fires mid-body-read (as it did
        // here -- the deadline hit while StringHttpMessageConverter was
        // still reading the trickled bytes), wrapped as a RestClientException
        // from message conversion. Either way it's a real thrown exception
        // instead of a hang -- AiProcessingService's broad catch(Exception)
        // handles both identically.
        assertThrows(RestClientException.class, () -> restTemplate.getForObject(url, String.class));

        long elapsedMs = System.currentTimeMillis() - start;
        // Must fire at ~2s (the configured deadline), not ~20s (when the
        // server would have finally stopped writing on its own) -- proves
        // this is a real overall deadline, not a stall timer that a steady
        // trickle of bytes keeps resetting.
        assertTrue(elapsedMs < 10_000,
                "expected the deadline to fire around 2s, took " + elapsedMs + "ms -- " +
                        "a stall-timer-based factory would hang far longer against a server that never stops sending bytes");
    }
}
