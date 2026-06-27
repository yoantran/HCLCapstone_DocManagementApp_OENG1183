    package org.example.hclcapstonebe;
    import org.springframework.beans.factory.annotation.Value;

    import org.springframework.boot.SpringApplication;
    import org.springframework.boot.autoconfigure.SpringBootApplication;
    import org.springframework.boot.context.event.*;
    import org.springframework.context.ApplicationListener;
    import org.springframework.context.ConfigurableApplicationContext;
    import org.springframework.context.event.ContextRefreshedEvent;

    @SpringBootApplication
    public class HclCapstoneBeApplication {

        static final long appStartMs          = System.currentTimeMillis();
        static long environmentReadyMs        = 0;
        static long beansDefinedMs            = 0;
        static long beansInitializedMs        = 0;  // Hikari + JPA done by here
        static long appStartedMs              = 0;
        static long appReadyMs                = 0;


        public static void main(String[] args) {
            SpringApplication app = new SpringApplication(HclCapstoneBeApplication.class);

            // ── 1. Properties + env loaded ────────────────────────────────────────
            app.addListeners((ApplicationListener<ApplicationEnvironmentPreparedEvent>)
                    e -> environmentReadyMs = System.currentTimeMillis());

            // ── 2. All bean definitions registered ───────────────────────────────
            app.addListeners((ApplicationListener<ApplicationPreparedEvent>)
                    e -> beansDefinedMs = System.currentTimeMillis());

            // ── 3. All beans initialized — Hikari pool + JPA done by now ─────────
            app.addListeners((ApplicationListener<ContextRefreshedEvent>)
                    e -> { if (beansInitializedMs == 0) beansInitializedMs = System.currentTimeMillis(); });

            // ── 4. App started ────────────────────────────────────────────────────
            app.addListeners((ApplicationListener<ApplicationStartedEvent>)
                    e -> appStartedMs = System.currentTimeMillis());

            // ── 5. Fully ready to serve requests ─────────────────────────────────
            app.addListeners((ApplicationListener<ApplicationReadyEvent>)
                    e -> appReadyMs = System.currentTimeMillis());

            ConfigurableApplicationContext ctx = app.run(args);
            long totalMs  = System.currentTimeMillis() - appStartMs;
            int  beanCount = ctx.getBeanDefinitionCount();


            System.out.printf("""
                                
                    ╔══════════════════════════════════════════════════════════════════╗
                    ║                HCL Capstone BE is running! 🚀                    ║
                    ╠══════════════════════════════════════════════════════════════════╣
                    ║  Backend API  : http://localhost:8080                             ║
                    ║  Swagger      : http://localhost:8080/swagger-ui/index.html       ║
                    ╠═════════════════════════╦════════════════════════════════════════╣
                    ║  Milestone              ║  Time since launch                     ║
                    ╠═════════════════════════╬════════════════════════════════════════╣
                    ║  ⚙️  Environment ready   ║  %-8s ms                              ║
                    ║  📋 Beans defined       ║  %-8s ms                              ║
                    ║  🔌 Hikari+JPA ready    ║  %-8s ms                              ║
                    ║  🚀 App started         ║  %-8s ms                              ║
                    ║  ✅ Fully ready         ║  %-8s ms                              ║
                    ╠═════════════════════════╬════════════════════════════════════════╣
                    ║  📦 Beans loaded        ║  %-6d                                 ║
                    ║  ⏱️  Total               ║  %-6d ms (~%.1f s)                    ║
                    ╚═════════════════════════╩════════════════════════════════════════╝
                    """,
                    ms(environmentReadyMs),
                    ms(beansDefinedMs),
                    ms(beansInitializedMs),
                    ms(appStartedMs),
                    ms(appReadyMs),
                    beanCount,
                    totalMs,
                    totalMs / 1000.0
            );
        }

        private static String ms(long timestamp) {
            return timestamp > 0 ? String.valueOf(timestamp - appStartMs) : "N/A";
        }
    }