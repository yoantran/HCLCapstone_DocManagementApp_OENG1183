
package org.example.hclcapstonebe.Config;

import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;
//validate service token
@Component("scanGuard")
@RequiredArgsConstructor
public class ScanGuard {

    private final ServiceTokenProvider tokenProvider;

    public boolean isAuthorized(HttpServletRequest request) {
        String token = request.getHeader("X-Service-Token");
        return token != null && tokenProvider.isValidScanToken(token);
    }
}