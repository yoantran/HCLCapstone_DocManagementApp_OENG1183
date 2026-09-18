package org.example.hclcapstonebe.Service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.example.hclcapstonebe.Audit.AuditEntry;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;

class AuditPersistenceServiceTest {

    // Far enough in the past that this can never collide with a real
    // audit-<date>.log file this service itself would ever create.
    private static final LocalDate TEST_DATE = LocalDate.of(1999, 1, 1);
    private static final Path TEST_FILE = Path.of("log/audit", "audit-" + TEST_DATE + ".log");

    private final AuditPersistenceService service = new AuditPersistenceService();

    @AfterEach
    void cleanup() throws IOException {
        Files.deleteIfExists(TEST_FILE);
    }

    // Real, confirmed bug: loadLogs() only caught IOException, but its own
    // deserialize() helper wraps every parse failure in an unchecked
    // RuntimeException -- a single corrupt line (e.g. from a crash
    // mid-append, or a manual edit) crashed the whole day's read instead
    // of just being skipped.
    @Test
    void loadLogs_skipsCorruptLineInsteadOfFailingTheWholeRead() throws IOException {
        Files.createDirectories(TEST_FILE.getParent());

        ObjectMapper mapper = new ObjectMapper().registerModule(new JavaTimeModule());
        AuditEntry validEntry = AuditEntry.builder()
                .timestamp(LocalDateTime.of(1999, 1, 1, 12, 0))
                .userId("u1")
                .name("Jo Worker")
                .email("jo@hcl.com")
                .role("STAFF")
                .method("GET")
                .path("/documents")
                .action("DocumentController.list")
                .status(200)
                .durationMs(5)
                .clientIp("127.0.0.1")
                .error(null)
                .build();

        Files.writeString(TEST_FILE,
                "{not valid json at all}\n" + mapper.writeValueAsString(validEntry) + "\n");

        List<AuditEntry> logs = service.loadLogs(TEST_DATE);

        assertEquals(1, logs.size(), "the one genuinely corrupt line must be skipped, not crash the whole read");
        assertEquals("jo@hcl.com", logs.get(0).getEmail());
    }
}
