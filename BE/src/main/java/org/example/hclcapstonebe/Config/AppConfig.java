package org.example.hclcapstonebe.Config;


import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.web.client.RestTemplate;

import java.net.http.HttpClient;
import java.time.Duration;

@Configuration
@EnableAsync
public class AppConfig {
    @Bean
    public RestTemplate restTemplate() {
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
        //
        // Issue #265 -- java.net.HttpURLConnection's read timeout (what
        // SimpleClientHttpRequestFactory used to use here) is an inter-read
        // stall timer, not a true overall deadline: any byte received (e.g.
        // Modal's own gateway keeping a long-running connection alive)
        // resets it, so a request whose server-side job got killed without
        // the connection itself closing can hang forever. Confirmed live --
        // a real upload hung 24+ minutes past the 180s cap with Modal's own
        // logs showing the job had already been cancelled server-side.
        // java.net.http.HttpClient's per-request timeout() is a genuine
        // overall-exchange deadline that fires regardless of keep-alive
        // traffic, so switching the factory closes this gap without
        // changing the configured timeout values or any calling code --
        // AiProcessingService's existing broad catch already handles
        // whatever exception this now reliably throws.
        // 5s connectTimeout was too short -- reproduced live (2026-09-06): a
        // request against a cold Modal container failed with "HTTP connect
        // timed out". Bumped to 30s, then 90s, and BOTH still failed cold
        // with the identical error -- container-side probing (docker exec +
        // wget against Modal's own /docs) showed connect-phase duration is
        // NOT simple TCP latency: it varied 7.6s / 7.6s / 12.7s / >60s
        // (timed out) across back-to-back calls, and a real upload still hit
        // the wall at ~90s. Modal's ASGI ingress appears to hold the
        // connection open while provisioning a cold container for ANY
        // request, including trivial ones -- the JDK HttpClient counts that
        // stall against connectTimeout, not the 180s readTimeout below. That
        // stall isn't reliably shorter than the cold-start budget this file
        // already accepts for the read phase (see the 60s->180s history
        // above), so give connect the same 180s rather than keep guessing a
        // smaller number empirically -- each guess costs a real Modal
        // cold-start to disprove.
        HttpClient httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(180))
                .build();
        JdkClientHttpRequestFactory factory = new JdkClientHttpRequestFactory(httpClient);
        factory.setReadTimeout(Duration.ofSeconds(180));
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
