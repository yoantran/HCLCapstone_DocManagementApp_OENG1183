package org.example.hclcapstonebe.Audit;

import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import org.example.hclcapstonebe.Service.AuditPersistenceService;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.util.*;

@Component
@RequiredArgsConstructor
public class AuditLogStore {

    private static final int MAX_ENTRIES = 1000;
    private final Deque<AuditEntry> buffer = new ArrayDeque<>(MAX_ENTRIES);
    private final AuditPersistenceService persistenceService;

    @PostConstruct
    public void init() {
        buffer.addAll(persistenceService.loadTodayLogs());
    }

    public synchronized void add(AuditEntry entry) {
        if (buffer.size() >= MAX_ENTRIES) {
            buffer.removeLast();          // evict oldest
        }

        buffer.addFirst(entry);           // newest first
        persistenceService.append(entry);
    }

    public List<AuditEntry> query(String userId, String method,
                                  String pathContains,
                                  LocalDate date,
                                  int limit) {
        List<AuditEntry> entries;

        if (date != null && !date.equals(LocalDate.now())) {
            entries = persistenceService.loadLogs(date);
        }
        else {
            entries = new ArrayList<>(buffer);
            if (date != null) {
                entries.removeIf(e -> !e.getTimestamp().toLocalDate().equals(date));
            }
        }

        return entries.stream()
                .filter(e -> userId == null || userId.equals(e.getUserId()))
                .filter(e -> method == null || method.equalsIgnoreCase(e.getMethod()))
                .filter(e -> pathContains == null || e.getPath().contains(pathContains))
                .limit(limit)
                .toList();
    }

    public synchronized int size() {
        return buffer.size();
    }

    public synchronized void clear() {
        buffer.clear();
    }
}