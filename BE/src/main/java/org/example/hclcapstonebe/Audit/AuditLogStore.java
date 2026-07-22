package org.example.hclcapstonebe.Audit;

import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Component
public class AuditLogStore {

    private static final int MAX_ENTRIES = 1000;
    private final Deque<AuditEntry> buffer = new ArrayDeque<>(MAX_ENTRIES);

    public synchronized void add(AuditEntry entry) {
        if (buffer.size() >= MAX_ENTRIES) {
            buffer.removeLast();          // evict oldest
        }
        buffer.addFirst(entry);           // newest first
    }

    public synchronized List<AuditEntry> query(String userId, String method,
                                               String pathContains, LocalDateTime since,
                                               int limit) {
        return buffer.stream()
                .filter(e -> userId == null || userId.equals(e.getUserId()))
                .filter(e -> method == null || method.equalsIgnoreCase(e.getMethod()))
                .filter(e -> pathContains == null || e.getPath().contains(pathContains))
                .filter(e -> since == null || e.getTimestamp().isAfter(since))
                .limit(limit)
                .collect(Collectors.toList());
    }

    public synchronized int size() {
        return buffer.size();
    }

    public synchronized void clear() {
        buffer.clear();
    }
}