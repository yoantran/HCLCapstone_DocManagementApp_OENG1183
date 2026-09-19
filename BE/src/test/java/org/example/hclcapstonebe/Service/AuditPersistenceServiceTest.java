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
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AuditPersistenceServiceTest {

    private static final LocalDate TEST_DATE = LocalDate.of(1999, 1, 1);
    private static final Path TEST_FILE = Path.of("log/audit", "audit-" + TEST_DATE + ".log");
    private static final Path TODAY_FILE = Path.of("log/audit", "audit-" + LocalDate.now() + ".log");

    private final AuditPersistenceService service = new AuditPersistenceService();

    @AfterEach
    void cleanup() throws IOException {
        Files.deleteIfExists(TEST_FILE);
        Files.deleteIfExists(TODAY_FILE);
    }

    @Test
    void init_createsDirectorySuccessfully() throws IOException {
        service.init();
        assertTrue(Files.exists(Path.of("log/audit")));
    }

    @Test
    void appendAndLoadTodayLogs_success() {
        AuditEntry entry = AuditEntry.builder()
                .timestamp(LocalDateTime.now())
                .userId("u1")
                .name("Jo Worker")
                .email("jo@hcl.com")
                .role("STAFF")
                .action("Test.append")
                .status(200)
                .build();

        // Test ghi log vào file hôm nay
        service.append(entry);

        // Test đọc log của ngày hôm nay
        List<AuditEntry> logs = service.loadTodayLogs();

        assertNotNull(logs);
        assertEquals(1, logs.size());
        assertEquals("jo@hcl.com", logs.get(0).getEmail());
    }

    @Test
    void loadTodayLogs_fileDoesNotExist_returnsEmptyList() {
        List<AuditEntry> logs = service.loadTodayLogs();

        assertNotNull(logs);
        assertTrue(logs.isEmpty());
    }

    @Test
    void loadLogs_fileDoesNotExist_returnsEmptyList() {
        List<AuditEntry> logs = service.loadLogs(LocalDate.of(1900, 1, 1));

        assertNotNull(logs);
        assertTrue(logs.isEmpty());
    }

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