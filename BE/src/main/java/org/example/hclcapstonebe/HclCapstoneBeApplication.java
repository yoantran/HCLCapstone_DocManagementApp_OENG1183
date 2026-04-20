package org.example.hclcapstonebe;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class HclCapstoneBeApplication {

    public static void main(String[] args) {
        SpringApplication.run(HclCapstoneBeApplication.class, args);

        System.out.println("""
                
                ╔══════════════════════════════════════════════════╗
                ║           HCL Capstone BE is running! 🚀         ║
                ╠══════════════════════════════════════════════════╣
                ║  Backend API  : http://localhost:8080             ║
                ║  Swagger API Doc   : http://localhost:8080/swagger-ui/index.html  ║
                ║  ║
                ╚══════════════════════════════════════════════════╝
                """);
    }
}
