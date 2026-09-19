package org.example.hclcapstonebe.Config;

import jakarta.servlet.FilterChain;
import org.example.hclcapstonebe.Entities.User;
import org.example.hclcapstonebe.Enums.RoleEnum;
import org.example.hclcapstonebe.Repository.UserRepository;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class SecurityAndJwtConfigTest {

    @Mock private UserRepository userRepository;
    @Mock private FilterChain filterChain;
    @Mock private AuthenticationConfiguration authConfig;

    @InjectMocks private UserDetailsServiceImpl userDetailsService;

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    private JwtUtil createJwtUtil() {
        JwtUtil jwtUtil = new JwtUtil();
        ReflectionTestUtils.setField(jwtUtil, "secret", "verySecretKeyThatIsAtLeast32BytesLongForHmacSha256!");
        ReflectionTestUtils.setField(jwtUtil, "expiration", 3600000L);
        return jwtUtil;
    }

    @Test
    void jwtUtil_and_userDetailsService_operations() {
        JwtUtil jwtUtil = createJwtUtil();
        String token = jwtUtil.generateToken("user@example.com");

        assertAll("JWT and UserDetails Verification",
                () -> assertTrue(jwtUtil.isTokenValid(token)),
                () -> assertEquals("user@example.com", jwtUtil.extractEmail(token)),
                () -> assertFalse(jwtUtil.isTokenValid("invalid.token.str")),
                () -> {
                    User user = new User();
                    user.setId(UUID.randomUUID());
                    user.setEmail("user@example.com");
                    user.setPassword("hashedPass");
                    user.setRole(RoleEnum.STAFF);

                    when(userRepository.findByEmailAndIsDeletedFalse("user@example.com")).thenReturn(Optional.of(user));
                    UserDetails details = userDetailsService.loadUserByUsername("user@example.com");
                    assertEquals("user@example.com", details.getUsername());
                    assertTrue(details.getAuthorities().stream().anyMatch(a -> a.getAuthority().equals("ROLE_STAFF")));
                },
                () -> {
                    when(userRepository.findByEmailAndIsDeletedFalse("missing@example.com")).thenReturn(Optional.empty());
                    assertThrows(UsernameNotFoundException.class, () -> userDetailsService.loadUserByUsername("missing@example.com"));
                }
        );
    }

    @Test
    void jwtAuthFilter_executionFlows() throws Exception {
        JwtUtil jwtUtil = createJwtUtil();
        String token = jwtUtil.generateToken("test@hcl.com");

        User user = new User();
        user.setEmail("test@hcl.com");
        user.setPassword("pass");
        user.setRole(RoleEnum.MANAGER);

        when(userRepository.findByEmailAndIsDeletedFalse("test@hcl.com")).thenReturn(Optional.of(user));

        JwtAuthFilter filter = new JwtAuthFilter(jwtUtil, userDetailsService);
        MockHttpServletRequest req = new MockHttpServletRequest();
        MockHttpServletResponse res = new MockHttpServletResponse();

        // Valid Token Header
        req.addHeader("Authorization", "Bearer " + token);
        filter.doFilterInternal(req, res, filterChain);

        assertNotNull(SecurityContextHolder.getContext().getAuthentication());
        assertEquals("test@hcl.com", SecurityContextHolder.getContext().getAuthentication().getName());
        verify(filterChain, times(1)).doFilter(req, res);

        // Missing Header
        SecurityContextHolder.clearContext();
        MockHttpServletRequest emptyReq = new MockHttpServletRequest();
        filter.doFilterInternal(emptyReq, res, filterChain);
        assertNull(SecurityContextHolder.getContext().getAuthentication());
    }

    @Test
    void securityAndSwaggerConfig_beansInitialization() throws Exception {
        SecurityConfig config = new SecurityConfig(mock(JwtAuthFilter.class));
        ReflectionTestUtils.setField(config, "allowedOrigins", new String[]{"http://localhost:3000"});

        assertAll("Security Config Beans",
                () -> assertNotNull(config.passwordEncoder()),
                () -> assertNotNull(config.corsConfigurationSource()),
                () -> new SwaggerConfig() // Instantiates SwaggerConfig for 100% constructor coverage
        );
    }
}