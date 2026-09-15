package org.example.hclcapstonebe.Service;

import org.example.hclcapstonebe.Enums.ScanStatus;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.ServerSocket;
import java.net.Socket;
import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTimeoutPreemptively;

class ClamAvScannerServiceTest {

    // Real, confirmed bug: the socket opened to the ClamAV daemon had no
    // setSoTimeout(), and the scan runs synchronously on the caller's
    // thread (the HTTP upload request thread in production). If ClamAV
    // accepts the TCP connection but hangs mid-protocol (overload,
    // deadlock, network partition after connect), the read blocked
    // forever with no way to recover short of a restart.
    //
    // Reproduces the exact shape with a real local server that accepts
    // the connection but never responds -- no mocking of Socket/IO
    // possible here since scanStream() opens its own socket internally,
    // so this is a real (bounded) integration test, not a unit test.
    @Test
    void scanStream_doesNotHangForeverWhenServerAcceptsButNeverResponds() throws IOException {
        ServerSocket hangingServer = new ServerSocket(0);
        int port = hangingServer.getLocalPort();

        Thread acceptThread = new Thread(() -> {
            try (Socket ignored = hangingServer.accept()) {
                Thread.sleep(60_000); // holds the connection open, never writes back
            } catch (Exception ignored2) {
                // server socket closed by the test tearing down -- expected
            }
        });
        acceptThread.setDaemon(true);
        acceptThread.start();

        ClamAvScannerService service = new ClamAvScannerService();
        ReflectionTestUtils.setField(service, "host", "localhost");
        ReflectionTestUtils.setField(service, "port", port);

        InputStream data = new ByteArrayInputStream("hello".getBytes());

        try {
            assertTimeoutPreemptively(Duration.ofSeconds(15), () -> {
                ClamAvScannerService.ScanResult result = service.scanStream(data);
                assertEquals(ScanStatus.ERROR, result.status());
            });
        } finally {
            hangingServer.close();
        }
    }
}
