package org.example.hclcapstonebe.Service;

import org.example.hclcapstonebe.Audit.AuditEntry;
import org.example.hclcapstonebe.Audit.AuditLogStore;
import org.example.hclcapstonebe.Service.AuditPersistenceService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class AuditLogStoreTest {

    @Mock
    private AuditPersistenceService persistenceService;

    @InjectMocks
    private AuditLogStore store;

    private AuditEntry entry(int i) {
        return AuditEntry.builder()
                .timestamp(LocalDateTime.now())
                .userId("u" + i)
                .name("n" + i)
                .email("e" + i + "@hcl.com")
                .role("STAFF")
                .method("GET")
                .path("/x/" + i)
                .action("a")
                .status(200)
                .durationMs(1)
                .clientIp("127.0.0.1")
                .error(null)
                .build();
    }

    @BeforeEach
    void setUp() {
        lenient().when(persistenceService.loadTodayLogs()).thenReturn(List.of());
        store.init();
    }

    @Test
    void add_size_clear_maxEntries_workingCorrectly() {
        for (int i = 0; i < AuditLogStore.maxEntries() + 10; i++) {
            store.add(entry(i));
        }

        assertEquals(AuditLogStore.maxEntries(), store.size());
        verify(persistenceService, times(AuditLogStore.maxEntries() + 10)).append(any());

        store.clear();
        assertEquals(0, store.size());
    }

    @Test
    void query_fromBufferWithFilters_returnsFilteredList() {
        AuditEntry entry1 = entry(1);
        AuditEntry entry2 = entry(2);
        store.add(entry1);
        store.add(entry2);

        List<AuditEntry> result = store.query("u1", "GET", "/x/1", LocalDate.now(), 10);

        assertEquals(1, result.size());
        assertEquals("u1", result.get(0).getUserId());
    }

    @Test
    void query_fromHistoricalFile_callsPersistenceService() {
        LocalDate pastDate = LocalDate.of(2020, 1, 1);
        AuditEntry oldEntry = entry(99);
        when(persistenceService.loadLogs(pastDate)).thenReturn(List.of(oldEntry));

        List<AuditEntry> result = store.query(null, null, null, pastDate, 10);

        assertEquals(1, result.size());
        assertEquals("u99", result.get(0).getUserId());
        verify(persistenceService, times(1)).loadLogs(pastDate);
    }

    @Test
    void concurrentAddAndQuery_neverThrows() throws InterruptedException {
        AtomicReference<Throwable> failure = new AtomicReference<>();
        ExecutorService pool = Executors.newFixedThreadPool(4);

        for (int i = 0; i < 2; i++) {
            pool.submit(() -> {
                for (int j = 0; j < 2000; j++) {
                    try {
                        store.add(entry(j));
                    } catch (Throwable t) {
                        failure.compareAndSet(null, t);
                    }
                }
            });
        }
        for (int i = 0; i < 2; i++) {
            pool.submit(() -> {
                for (int j = 0; j < 2000; j++) {
                    try {
                        store.query(null, null, null, null, 100);
                    } catch (Throwable t) {
                        failure.compareAndSet(null, t);
                    }
                }
            });
        }

        pool.shutdown();
        pool.awaitTermination(30, TimeUnit.SECONDS);

        assertNull(failure.get(), "concurrent add()/query() must never throw: " + failure.get());
    }
}