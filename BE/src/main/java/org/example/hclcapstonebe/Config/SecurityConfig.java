package org.example.hclcapstonebe.Config;

import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.*;
import org.springframework.security.authentication.*;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.Collections;
import java.util.List;

@Configuration
@EnableMethodSecurity
@RequiredArgsConstructor
public class SecurityConfig {

    private final JwtAuthFilter jwtAuthFilter;

    @Value("${app.cors.allowed-origins}")
    private String[] allowedOrigins;

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        return http
                .cors(cors -> cors.configurationSource(corsConfigurationSource()))
                .csrf(AbstractHttpConfigurer::disable)
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers(
                                "/auth/**",
                                "/swagger-ui/**",
                                "/swagger-ui.html",
                                "/v3/api-docs/**",
                                "/swagger-resources/**",
                                "/webjars/**",
                                "/ws/**",
                                "/dev/**" // ← add this
                        ).permitAll()
                        .requestMatchers("/admin/**").hasRole("ADMIN")
                        .requestMatchers("/documents/department/**").hasRole("MANAGER@Service\n" +
                                "@RequiredArgsConstructor\n" +
                                "public class NotificationService {\n" +
                                "\n" +
                                "    private final NotificationRepository notificationRepository;\n" +
                                "    private final UserRepository userRepository;\n" +
                                "    private final NotificationMapper notificationMapper;\n" +
                                "\n" +
                                "    public List<NotificationResponse> getMyNotifications(String email) {\n" +
                                "        var user = userRepository.findByEmailAndIsDeletedFalse(email)\n" +
                                "                .orElseThrow(() -> new AppException(\"User not found\", HttpStatus.NOT_FOUND));\n" +
                                "\n" +
                                "        return notificationRepository\n" +
                                "                .findByReceiverIdOrderByCreatedAtDesc(user.getId())\n" +
                                "                .stream()\n" +
                                "                .map(notificationMapper::toResponse)\n" +
                                "                .collect(Collectors.toList());\n" +
                                "    }\n" +
                                "\n" +
                                "    public NotificationResponse markAsRead(UUID notifId, String email) {\n" +
                                "        var user = userRepository.findByEmailAndIsDeletedFalse(email)\n" +
                                "                .orElseThrow(() -> new AppException(\"User not found\", HttpStatus.NOT_FOUND));\n" +
                                "\n" +
                                "        Notification notif = notificationRepository.findById(notifId)\n" +
                                "                .orElseThrow(() -> new AppException(\"Notification not found\", HttpStatus.NOT_FOUND));\n" +
                                "\n" +
                                "        if (!notif.getReceiver().getId().equals(user.getId())) {\n" +
                                "            throw new AppException(\"Access denied\", HttpStatus.FORBIDDEN);\n" +
                                "        }\n" +
                                "\n" +
                                "        notif.setHasRead(true);\n" +
                                "        notif.setIsReadDateTime(LocalDateTime.now());\n" +
                                "        notificationRepository.save(notif);\n" +
                                "\n" +
                                "        return notificationMapper.toResponse(notif);\n" +
                                "    }\n" +
                                "}")
                        .anyRequest().authenticated())
                .addFilterBefore(jwtAuthFilter, UsernamePasswordAuthenticationFilter.class)
                .build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public AuthenticationManager authenticationmanager(AuthenticationConfiguration config)
            throws Exception {
        return config.getAuthenticationManager();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration corsConfiguration = new CorsConfiguration();
        corsConfiguration.setAllowedOrigins(List.of(allowedOrigins));
        corsConfiguration.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE", "PATCH"));
        corsConfiguration.setAllowedHeaders(Collections.singletonList("*"));
        corsConfiguration.setAllowCredentials(true);
        corsConfiguration.setMaxAge(3600L);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        // apply to all endpoints
        source.registerCorsConfiguration("/**", corsConfiguration);

        return source;
    }
}
