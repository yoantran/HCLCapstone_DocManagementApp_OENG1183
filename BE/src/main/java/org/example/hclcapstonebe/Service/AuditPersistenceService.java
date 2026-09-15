package org.example.hclcapstonebe.Service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import org.example.hclcapstonebe.Audit.AuditEntry;
import org.springframework.stereotype.Service;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Stream;

@Service
@RequiredArgsConstructor
public class AuditPersistenceService {
    private static final String LOG_FOLDER = "log/audit";

    private final ObjectMapper mapper = new ObjectMapper()
            .registerModule(new JavaTimeModule());

    @PostConstruct
    public void init() throws IOException {
        Files.createDirectories(Path.of(LOG_FOLDER));
    }

    // Append one audit entry to today's log file.
    public synchronized void append(AuditEntry entry) {

        try {

            Path file = todayLogFile();

            try (BufferedWriter writer = Files.newBufferedWriter(
                    file,
                    StandardOpenOption.CREATE,
                    StandardOpenOption.APPEND
            )) {
                writer.write(mapper.writeValueAsString(entry));
                writer.newLine();
            }

        } catch (IOException e) {
            System.err.println("Failed to persist audit log: " + e.getMessage());
        }
    }

    public List<AuditEntry> loadTodayLogs() {
        List<AuditEntry> logs = new ArrayList<>();

        try {
            Path file = todayLogFile();

            if (!Files.exists(file))
                return logs;

            for (String line : Files.readAllLines(file)) {
                if (line.isBlank())
                    continue;
                logs.add(mapper.readValue(line, AuditEntry.class));
            }
        } catch (Exception e) {
            System.err.println("Failed loading audit logs: " + e.getMessage());
        }

        return logs;
    }

    private Path todayLogFile() {
        return Path.of(
                LOG_FOLDER,
                "audit-" + LocalDate.now() + ".log"
        );
    }

    public List<AuditEntry> loadLogs(LocalDate date) {
        List<AuditEntry> result = new ArrayList<>();

        Path file = Path.of(LOG_FOLDER, "audit-" + date + ".log");

        if (!Files.exists(file)) {
            return List.of();
        }

        try (Stream<String> lines = Files.lines(file)) {
            // Real, confirmed bug: this used to .map(this::deserialize),
            // whose own RuntimeException (any parse failure) was never
            // caught here -- a single corrupt line (e.g. from a crash
            // mid-append, or a manual edit) failed the ENTIRE day's read
            // instead of just being skipped. Each line is now handled
            // independently: a bad line is logged and skipped, every
            // other valid line in the file still comes back.
            lines.filter(s -> !s.isBlank())
                    .forEach(line -> {
                        try {
                            result.add(deserialize(line));
                        } catch (RuntimeException e) {
                            System.err.println("Skipping corrupt audit log line in " + file + ": " + e.getMessage());
                        }
                    });
        }
        catch (IOException e) {
            System.out.print("Cannot read " + file + " " + e);
        }

        return result;
    }

    private AuditEntry deserialize(String line) {
        try {
            return mapper.readValue(line, AuditEntry.class);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}
