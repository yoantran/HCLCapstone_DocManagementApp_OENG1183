package org.example.hclcapstonebe.Config;


import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.web.client.RestTemplate;

@Configuration
@EnableAsync
public class AppConfig {
    @Bean
    public RestTemplate restTemplate() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(5_000);
        // 60s was too short -- confirmed against a real running AI service:
        // a genuine cold start (first request after container restart, model
        // loading alone) takes ~90s, and the AI service processes /process
        // requests synchronously (one at a time, no worker concurrency), so
        // any request queued behind another real OCR call adds its full
        // duration on top. Reproduced this exact 60s timeout twice against
        // the real deployed container -- documents got permanently stuck at
        // aiProcessed=false because BE gave up before AI's response arrived.
        // 180s covers observed worst-case (~2min) with margin. The one-
        // request-at-a-time bottleneck itself is a separate, real issue
        // (see #195) -- this timeout bump doesn't fix throughput under
        // real concurrent load, only stops premature client-side giveup on
        // a single request that was always going to succeed if BE had waited.
        factory.setReadTimeout(180_000);
        return new RestTemplate(factory);
    }

    // HikariCP pool is only 3 connections (application.properties) -- kept small
    // to leave headroom for the main request thread's own connection.
    @Bean(name = "aiTaskExecutor")
    public ThreadPoolTaskExecutor aiTaskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(2);
        executor.setMaxPoolSize(2);
        executor.setQueueCapacity(50);
        executor.setThreadNamePrefix("ai-process-");
        executor.initialize();
        return executor;
    }
}
