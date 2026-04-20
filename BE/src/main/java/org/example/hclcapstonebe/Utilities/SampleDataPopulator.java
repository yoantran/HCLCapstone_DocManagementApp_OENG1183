package org.example.hclcapstonebe.Utilities;

import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import lombok.extern.slf4j.Slf4j;
import org.example.hclcapstonebe.Enums.DocumentFormatEnum;
import org.example.hclcapstonebe.Enums.DocumentTypeEnum;
import org.example.hclcapstonebe.Enums.RoleEnum;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;
import lombok.RequiredArgsConstructor;

import java.time.LocalDateTime;
import java.util.UUID;

@Slf4j
@Component
@RequiredArgsConstructor
public class SampleDataPopulator {

    @PersistenceContext
    private EntityManager em;

    private final PasswordEncoder passwordEncoder;


    @Transactional
    public void clear() {
        log.info("🧹 Clearing...");

        // Delete child tables first
        em.createNativeQuery("DELETE FROM notifications").executeUpdate();
        em.createNativeQuery("DELETE FROM documents").executeUpdate();

        // Delete users first (removes the FK reference from departments.boss_id)
        // but we need to drop the boss_id FK constraint temporarily
        // → Easiest: alter column to allow null, delete, then restore
        em.createNativeQuery("ALTER TABLE departments ALTER COLUMN boss_id DROP NOT NULL").executeUpdate();
        em.createNativeQuery("UPDATE departments SET boss_id = NULL").executeUpdate();
        em.createNativeQuery("DELETE FROM users").executeUpdate();
        em.createNativeQuery("DELETE FROM departments").executeUpdate();
        em.createNativeQuery("ALTER TABLE departments ALTER COLUMN boss_id SET NOT NULL").executeUpdate();

        log.info("🧹 Done clearing.");
    }
    @Transactional
    public void insert() {
        String pw = passwordEncoder.encode("password123");
        LocalDateTime now = LocalDateTime.now();

        // ── Admin ──────────────────────────────────────────
        String adminId = uuid();
        insertUser(adminId, "admin@hcl.com", pw, "System Admin", "0900000000", RoleEnum.ADMIN, null, now);

        // ── Bosses ─────────────────────────────────────────
        String[] bossIds   = {uuid(), uuid(), uuid(), uuid(), uuid()};
        String[] bossNames = {"Boss1", "Tran Thi Boss", "Le Van Boss", "Pham Thi Boss", "Hoang Van Boss"};
        String[] bossEmails= {"boss1@hcl.com","boss.finance@hcl.com","boss.hr@hcl.com","boss.marketing@hcl.com","boss.operations@hcl.com"};
        String[] bossPhones= {"0901111111","0902222222","0903333333","0904444444","0905555555"};

        for (int i = 0; i < 5; i++) {
            insertUser(bossIds[i], bossEmails[i], pw, bossNames[i], bossPhones[i], RoleEnum.BOSS, null, now);
        }

        // ── Departments ────────────────────────────────────
        String[] deptIds   = {uuid(), uuid(), uuid(), uuid(), uuid()};
        String[] deptNames = {"Engineering","Finance","Human Resources","Marketing","Operations"};

        for (int i = 0; i < 5; i++) {
            insertDept(deptIds[i], deptNames[i], bossIds[i], now);
        }

        // ── Assign dept to bosses ──────────────────────────
        for (int i = 0; i < 5; i++) {
            em.createNativeQuery("UPDATE users SET department_id = ? WHERE id = ?")
                    .setParameter(1, deptIds[i])
                    .setParameter(2, bossIds[i])
                    .executeUpdate();
        }

        // ── Staff ──────────────────────────────────────────
        String[][] staffData = {
                {"Staff1",            "staff1@hcl.com",             "0911111111"},
                {"Tran Thi Bich",     "bich.engineering@hcl.com",   "0911111112"},
                {"Le Van Cuong",      "cuong.engineering@hcl.com",  "0911111113"},
                {"Pham Thi Dung",     "dung.engineering@hcl.com",   "0911111114"},
                {"Hoang Van Em",      "em.finance@hcl.com",         "0922222221"},
                {"Nguyen Thi Phuong", "phuong.finance@hcl.com",     "0922222222"},
                {"Tran Van Giang",    "giang.finance@hcl.com",      "0922222223"},
                {"Le Thi Hoa",        "hoa.finance@hcl.com",        "0922222224"},
                {"Pham Van Hung",     "hung.hr@hcl.com",            "0933333331"},
                {"Hoang Thi Lan",     "lan.hr@hcl.com",             "0933333332"},
                {"Nguyen Van Minh",   "minh.hr@hcl.com",            "0933333333"},
                {"Tran Thi Ngoc",     "ngoc.hr@hcl.com",            "0933333334"},
                {"Le Van Phuc",       "phuc.marketing@hcl.com",     "0944444441"},
                {"Pham Thi Quynh",    "quynh.marketing@hcl.com",    "0944444442"},
                {"Hoang Van Son",     "son.marketing@hcl.com",      "0944444443"},
                {"Nguyen Thi Thao",   "thao.marketing@hcl.com",     "0944444444"},
                {"Tran Van Tuan",     "tuan.operations@hcl.com",    "0955555551"},
                {"Le Thi Uyen",       "uyen.operations@hcl.com",    "0955555552"},
                {"Pham Van Vinh",     "vinh.operations@hcl.com",    "0955555553"},
                {"Hoang Thi Xuan",    "xuan.operations@hcl.com",    "0955555554"},
        };

        for (int i = 0; i < 20; i++) {
            insertUser(uuid(), staffData[i][1], pw, staffData[i][0],
                    staffData[i][2], RoleEnum.STAFF, deptIds[i / 4],
                    now.minusDays(i));
        }

        log.info("✅ Seeding done! Users and departments created.");
        log.info("📋 Password for all accounts: password123");
    }

    // ─── HELPERS ──────────────────────────────────────────

    private void insertUser(String id, String email, String pw, String name,
                            String phone, RoleEnum role, String deptId, LocalDateTime created) {
        em.createNativeQuery("""
            INSERT INTO users
              (id, email, password, name, phone_number, role_enum,
               department_id, is_deleted, created_at_date_time)
            VALUES (?,?,?,?,?,?,?,false,?)
            """)
                .setParameter(1, id)
                .setParameter(2, email)
                .setParameter(3, pw)
                .setParameter(4, name)
                .setParameter(5, phone)
                .setParameter(6, role.name())
                .setParameter(7, deptId)
                .setParameter(8, created)
                .executeUpdate();
    }

    private void insertDept(String id, String name, String bossId, LocalDateTime created) {
        em.createNativeQuery("""
            INSERT INTO departments (id, name, boss_id, created_at_date_time)
            VALUES (?,?,?,?)
            """)
                .setParameter(1, id)
                .setParameter(2, name)
                .setParameter(3, bossId)
                .setParameter(4, created)
                .executeUpdate();
    }

    private String uuid() {
        return UUID.randomUUID().toString();
    }
}