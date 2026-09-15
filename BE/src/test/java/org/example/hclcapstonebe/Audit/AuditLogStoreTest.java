package org.example.hclcapstonebe.Audit;

import org.example.hclcapstonebe.Service.AuditPersistenceService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.assertNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class AuditLogStoreTest {

    @Mock
    private AuditPersistenceService persistenceService;

    private AuditEntry entry(int i) {
        return AuditEntry.builder()
                .timestamp(LocalDateTime.now())
                .userId("u" + i)
                .name("n")
                .email("e@hcl.com")
                .role("STAFF")
                .method("GET")
                .path("/x")
                .action("a")
                .status(200)
                .durationMs(1)
                .clientIp("127.0.0.1")
                .error(null)
                .build();
    }

    // Real, confirmed bug: query() copied the shared ArrayDeque via
    // `new ArrayList<>(buffer)` with no lock, while add() mutates that same
    // deque under `synchronized`. Concurrent add() + query() could throw
    // ConcurrentModificationException. copyBuffer() is now synchronized too.
    @Test
    void concurrentAddAndQuery_neverThrows() throws InterruptedException {
        lenient().when(persistenceService.loadTodayLogs()).thenReturn(List.of());
        AuditLogStore store = new AuditLogStore(persistenceService);

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
