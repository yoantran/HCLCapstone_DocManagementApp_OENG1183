package org.example.hclcapstonebe.Utilities;

import jakarta.persistence.EntityManager;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.util.ReflectionTestUtils;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

@ExtendWith(MockitoExtension.class)
class SampleDataPopulatorTest {

    @Mock
    private EntityManager em;

    @Mock
    private PasswordEncoder passwordEncoder;

    // Real, confirmed bug: clear() ran unconditionally with no guard --
    // running SampleDataRunner.main() by accident (a stray IDE run-config,
    // a CI job reusing the same application.properties) wipes
    // users/documents/departments/notifications with no confirmation, on
    // whatever datasource is configured -- for this project, the one real
    // Supabase DB (no dev/prod split exists). ALLOW_DATA_WIPE must be
    // explicitly set to "true" for clear() to touch the database at all.
    @Test
    void clear_refusesToRunWithoutExplicitOptIn() {
        SampleDataPopulator populator = new SampleDataPopulator(passwordEncoder);
        ReflectionTestUtils.setField(populator, "em", em);

        assertThrows(IllegalStateException.class, populator::clear);

        verify(em, never()).createNativeQuery(anyString());
    }
}
