package org.example.hclcapstonebe.Utilities;

import org.example.hclcapstonebe.HclCapstoneBeApplication;
import org.springframework.boot.SpringApplication;
import org.springframework.context.ConfigurableApplicationContext;

public class SampleDataRunner {

    public static void main(String[] args) {
        // ← Boot from YOUR main app class so all beans/repos are scanned
        ConfigurableApplicationContext context =
                SpringApplication.run(HclCapstoneBeApplication.class, args);

        SampleDataPopulator populator = context.getBean(SampleDataPopulator.class);

        populator.clear();   // ← called via Spring proxy ✅
        populator.insert();  // ← called via Spring proxy ✅

        context.close();
        context.close();
        System.exit(0);
    }
}