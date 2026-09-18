package org.example.hclcapstonebe.Config;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.http.HttpClient;
import java.time.Duration;
import java.util.Base64;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Regression coverage for a real bug found 2026-09-06: RestTemplate's
 * readTimeout is a genuine overall-exchange deadline (see AppConfig's own
 * comment history for why JdkClientHttpRequestFactory was chosen). When it
 * fires mid-body-read, JDK's HttpClient cancels the response subscription,
 * and Spring wraps the resulting IOException in a RestClientException whose
 * message ("Error while extracting response for type ... and content type
 * ...") is textually indistinguishable from a "no compatible converter"
 * error -- this previously led to misdiagnosing a real apply-redaction
 * timeout as an image/png HttpMessageConverter registration bug.
 */
class AiServiceRestTemplateTimeoutTest {

    // Minimal valid 1x1 red PNG.
    private static final byte[] PNG_BYTES = Base64.getDecoder().decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    );

    private HttpServer server;
    private String baseUrl;

    @BeforeEach
    void startServer() throws Exception {
        server = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
        server.createContext("/image", exchange -> {
            exchange.getRequestBody().readAllBytes();
            exchange.getResponseHeaders().add("Content-Type", "image/png");
            // 0 length forces chunked transfer-encoding, matching how
            // FastAPI/Starlette (Modal's stack) streams responses.
            exchange.sendResponseHeaders(200, 0);
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(PNG_BYTES, 0, 10);
                os.flush();
                try {
                    Thread.sleep(300);
                } catch (InterruptedException ignored) {
                    Thread.currentThread().interrupt();
                }
                os.write(PNG_BYTES, 10, PNG_BYTES.length - 10);
            }
            exchange.close();
        });
        server.start();
        baseUrl = "http://localhost:" + server.getAddress().getPort() + "/image";
    }

    @AfterEach
    void stopServer() {
        server.stop(0);
    }

    private RestTemplate restTemplateWithReadTimeout(Duration readTimeout) {
        HttpClient httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build();
        JdkClientHttpRequestFactory factory = new JdkClientHttpRequestFactory(httpClient);
        factory.setReadTimeout(readTimeout);
        return new RestTemplate(factory);
    }

    @Test
    void byteArrayConverterIsRegisteredForImagePng() {
        RestTemplate restTemplate = restTemplateWithReadTimeout(Duration.ofSeconds(5));
        boolean canRead = restTemplate.getMessageConverters().stream()
                .anyMatch(c -> c.canRead(byte[].class, MediaType.IMAGE_PNG));
        assertTrue(canRead, "no registered HttpMessageConverter can read byte[]+image/png");
    }

    @Test
    void responseWithinReadTimeoutSucceeds() {
        RestTemplate restTemplate = restTemplateWithReadTimeout(Duration.ofSeconds(5));
        ResponseEntity<byte[]> response = restTemplate.exchange(
                baseUrl, HttpMethod.GET, HttpEntity.EMPTY, byte[].class);
        assertArrayEquals(PNG_BYTES, response.getBody());
    }

    @Test
    void readTimeoutFiringMidBodyThrowsRestClientException() {
        // Server stalls 300ms mid-body (see startServer); this client gives
        // up after 50ms, well before the stall ends.
        RestTemplate restTemplate = restTemplateWithReadTimeout(Duration.ofMillis(50));
        assertThrows(RestClientException.class, () -> restTemplate.exchange(
                baseUrl, HttpMethod.GET, HttpEntity.EMPTY, byte[].class));
    }
}
