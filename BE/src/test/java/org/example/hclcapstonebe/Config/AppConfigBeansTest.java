package org.example.hclcapstonebe.Config;

import org.junit.jupiter.api.Test;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

class AppConfigBeansTest {

    @Test
    void aiTaskExecutor_initializesWithCorrectSettings() {
        AppConfig appConfig = new AppConfig();
        ThreadPoolTaskExecutor executor = appConfig.aiTaskExecutor();

        assertNotNull(executor);
        assertEquals(2, executor.getCorePoolSize());
        assertEquals(2, executor.getMaxPoolSize());
        assertEquals("ai-process-", executor.getThreadNamePrefix());

        executor.shutdown();
    }
}