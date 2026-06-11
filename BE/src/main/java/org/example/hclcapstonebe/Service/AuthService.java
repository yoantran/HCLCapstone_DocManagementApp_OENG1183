package org.example.hclcapstonebe.Service;



import lombok.RequiredArgsConstructor;
import org.example.hclcapstonebe.Config.JwtUtil;
import org.example.hclcapstonebe.DTO.Request.LoginRequest;
import org.example.hclcapstonebe.DTO.Response.AuthResponse;
import org.example.hclcapstonebe.Exception.AppException;
import org.example.hclcapstonebe.Repository.UserRepository;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;

    @Transactional(readOnly = true)
    public AuthResponse login(LoginRequest request) {
        var user = userRepository.findByEmailAndIsDeletedFalse(request.getEmail())
                .orElseThrow(() -> new AppException("Invalid credentials", HttpStatus.UNAUTHORIZED));

        if (!passwordEncoder.matches(request.getPassword(), user.getPassword())) {
            throw new AppException("Invalid credentials", HttpStatus.UNAUTHORIZED);
        }

        String token = jwtUtil.generateToken(user.getEmail());
        String departmentId = user.getDepartment() != null
                ? user.getDepartment().getId().toString()
                : null;
        return new AuthResponse(String.valueOf(user.getId()), token, user.getRole().name(), user.getEmail(), user.getName(), departmentId);
    }

    // Logout: on client side, discard the token.
    // For server-side blacklist, add a token blacklist table (optional).
    public void logout() {
        // Stateless JWT: client drops the token.
        // Add token blacklist here if needed.
    }
}