package org.example.hclcapstonebe.Controller;

import org.example.hclcapstonebe.Audit.AuditLogStore;
import org.example.hclcapstonebe.Service.AuditPersistenceService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class AdminAuditLogControllerTest {

    @Mock
    private AuditPersistenceService persistenceService;

    // Real, confirmed bug: getLogs() only clamped the upper bound
    // (Math.min(limit, 1000)) before passing it to store.query(), which
    // ultimately calls Stream.limit(limit). A negative limit reached
    // Stream.limit(-1), which throws IllegalArgumentException per its
    // contract -- an uncaught 500 instead of a 400.
    @Test
    void getLogs_negativeLimit_doesNotThrow() {
        lenient().when(persistenceService.loadTodayLogs()).thenReturn(List.of());
        AuditLogStore store = new AuditLogStore(persistenceService);
        AdminAuditLogController controller = new AdminAuditLogController(store);

        ResponseEntity<List<org.example.hclcapstonebe.DTO.Response.AuditLogResponse>> response =
                controller.getLogs(null, null, null, null, -1);

        assertEquals(HttpStatus.OK, response.getStatusCode());
    }

    // Real, confirmed bug: stats() hardcoded "capacity": 1000 as a literal,
    // a 3rd independent copy of AuditLogStore.MAX_ENTRIES (the query() limit
    // clamp was the 2nd). If MAX_ENTRIES ever changes, this response would
    // silently keep reporting the old value. Now reads AuditLogStore.maxEntries().
    @Test
    void stats_capacityReflectsAuditLogStoreMaxEntries() {
        lenient().when(persistenceService.loadTodayLogs()).thenReturn(List.of());
        AuditLogStore store = new AuditLogStore(persistenceService);
        AdminAuditLogController controller = new AdminAuditLogController(store);

        ResponseEntity<Map<String, Object>> response = controller.stats();

        assertEquals(AuditLogStore.maxEntries(), response.getBody().get("capacity"));
    }
}
