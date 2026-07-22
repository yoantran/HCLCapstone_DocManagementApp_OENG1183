package org.example.hclcapstonebe.Service;

import lombok.extern.slf4j.Slf4j;
import org.example.hclcapstonebe.Enums.ScanStatus;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@Service
public class ClamAvScannerService {
    public record ScanResult(ScanStatus status, String message) {
        public boolean isClean() {
            return status == ScanStatus.CLEAN;
        }
    }

    @Value("${clamav.host}")
    private String host;

    @Value("${clamav.port}")
    private int port;

    /**
     * Scans an input stream for viruses using ClamAV INSTREAM protocol over a raw socket.
     *
     * @param inputStream the data stream to scan
     * @return true if the stream is clean ("STREAM OK"), false if infected ("FOUND") or if scan failed
     */
    public ScanResult scanStream(InputStream inputStream) {
        log.info("Initiating ClamAV scan on host: {}, port: {}", host, port);

        try (Socket socket = new Socket(host, port);
             OutputStream out = socket.getOutputStream();
             InputStream in = socket.getInputStream();
             InputStream is = inputStream) {

            // Write ClamAV INSTREAM command
            out.write("nINSTREAM\n".getBytes(StandardCharsets.UTF_8));

            // Chunk transfer: 4096 bytes buffer
            byte[] buffer = new byte[4096];
            int bytesRead;
            while ((bytesRead = is.read(buffer)) != -1) {
                // Write chunk size as 4-byte big-endian unsigned integer
                byte[] lengthBytes = new byte[4];
                lengthBytes[0] = (byte) ((bytesRead >>> 24) & 0xFF);
                lengthBytes[1] = (byte) ((bytesRead >>> 16) & 0xFF);
                lengthBytes[2] = (byte) ((bytesRead >>> 8) & 0xFF);
                lengthBytes[3] = (byte) (bytesRead & 0xFF);

                out.write(lengthBytes);
                out.write(buffer, 0, bytesRead);
            }

            // Signal end of stream with a 4-byte zero length terminator
            byte[] terminator = new byte[]{0, 0, 0, 0};
            out.write(terminator);
            out.flush();

            // Read ClamAV response
            ByteArrayOutputStream responseBytes = new ByteArrayOutputStream();
            byte[] responseBuffer = new byte[1024];
            int readBytes;
            while ((readBytes = in.read(responseBuffer)) != -1) {
                responseBytes.write(responseBuffer, 0, readBytes);
            }

            String response = responseBytes.toString(StandardCharsets.UTF_8).trim();
            log.info("ClamAV response received: {}", response);

            if (response.contains("OK")) {
                return new ScanResult(ScanStatus.CLEAN, "No malware detected.");
            } else if (response.contains("FOUND")) {
                log.warn("ClamAV scan: Threat found. Verdict: {}", response);
                String signature = "Unknown malware";
                Matcher matcher = Pattern.compile(":\\s*(.+?)\\s+FOUND").matcher(response);
                if (matcher.find()) {
                    signature = matcher.group(1);
                }

                return new ScanResult(
                        ScanStatus.INFECTED,
                        "Malware detected (" + signature + "). Document quarantined."
                );
            } else {
                log.warn("ClamAV scan: Unrecognized signature or anomaly detected. Verdict: {}", response);
                return new ScanResult(
                        ScanStatus.ERROR,
                        "Malware scan returned an unrecognized response."
                );
            }

        } catch (IOException e) {
            log.error("ClamAV scanning failed due to connection/IO error: {}", e.getMessage(), e);
            return new ScanResult(
                    ScanStatus.ERROR,
                    "Malware scan failed due to a scanner connection error."
            );
        }
    }
}
