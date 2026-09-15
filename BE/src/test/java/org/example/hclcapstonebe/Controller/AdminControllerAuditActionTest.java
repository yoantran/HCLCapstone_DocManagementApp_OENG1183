package org.example.hclcapstonebe.Controller;

import org.example.hclcapstonebe.Audit.AuditAction;
import org.example.hclcapstonebe.DTO.Request.CreateUserRequest;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;

import static org.junit.jupiter.api.Assertions.assertEquals;

class AdminControllerAuditActionTest {

    // Real, confirmed bug: @AuditAction("Created user '{email}'") can never
    // resolve -- createUser()'s only parameter is named `req`, so the
    // placeholder must be `{req.email}` (AuditAspect only substitutes
    // `{paramName}` / `{paramName.field}`). Every user-creation audit entry
    // literally read "Created user '{email}'" instead of the real address.
    @Test
    void createUser_auditActionPlaceholderMatchesParamName() throws NoSuchMethodException {
        Method createUser = AdminController.class.getMethod("createUser", CreateUserRequest.class);
        AuditAction auditAction = createUser.getAnnotation(AuditAction.class);

        assertEquals("Created user '{req.email}'", auditAction.value());
    }
}
