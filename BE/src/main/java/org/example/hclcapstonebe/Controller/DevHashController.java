package org.example.hclcapstonebe.Controller;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.ExampleObject;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
@RestController
@RequestMapping("/dev")
class DevHashController {
    @GetMapping("/hash")
    public String hash(@RequestParam String raw) {
        return new org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder().encode(raw);
    }
}
