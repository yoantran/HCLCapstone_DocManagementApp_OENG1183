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

        em.createNativeQuery("DELETE FROM notifications").executeUpdate();
        em.createNativeQuery("DELETE FROM documents").executeUpdate();
        em.createNativeQuery("UPDATE departments SET boss_id = NULL").executeUpdate();
        em.createNativeQuery("DELETE FROM users").executeUpdate();
        em.createNativeQuery("DELETE FROM departments").executeUpdate();
        log.info("🧹 Done clearing.");

    }

    @Transactional
    public void insert() {
        String pw = passwordEncoder.encode("password123");
        LocalDateTime now = LocalDateTime.now();

        // ── Admin ──────────────────────────────────────────
        String adminId = uuid();
        insertUser(adminId, "admin@hcl.com", pw, "System Admin", "0900000000", RoleEnum.ADMIN, null, now);

        // ── Boss IDs ───────────────────────────────────────
        String[] bossIds   = {uuid(), uuid(), uuid(), uuid(), uuid()};
        String[] bossNames = {"Nguyen Van Boss", "Tran Thi Boss", "Le Van Boss", "Pham Thi Boss", "Hoang Van Boss"};
        String[] bossEmails= {"boss.engineering@hcl.com","boss.finance@hcl.com","boss.hr@hcl.com","boss.marketing@hcl.com","boss.operations@hcl.com"};
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
                {"Nguyen Van An",     "an.engineering@hcl.com",    "0911111111"},
                {"Tran Thi Bich",     "bich.engineering@hcl.com",  "0911111112"},
                {"Le Van Cuong",      "cuong.engineering@hcl.com", "0911111113"},
                {"Pham Thi Dung",     "dung.engineering@hcl.com",  "0911111114"},
                {"Hoang Van Em",      "em.finance@hcl.com",        "0922222221"},
                {"Nguyen Thi Phuong", "phuong.finance@hcl.com",    "0922222222"},
                {"Tran Van Giang",    "giang.finance@hcl.com",     "0922222223"},
                {"Le Thi Hoa",        "hoa.finance@hcl.com",       "0922222224"},
                {"Pham Van Hung",     "hung.hr@hcl.com",           "0933333331"},
                {"Hoang Thi Lan",     "lan.hr@hcl.com",            "0933333332"},
                {"Nguyen Van Minh",   "minh.hr@hcl.com",           "0933333333"},
                {"Tran Thi Ngoc",     "ngoc.hr@hcl.com",           "0933333334"},
                {"Le Van Phuc",       "phuc.marketing@hcl.com",    "0944444441"},
                {"Pham Thi Quynh",    "quynh.marketing@hcl.com",   "0944444442"},
                {"Hoang Van Son",     "son.marketing@hcl.com",     "0944444443"},
                {"Nguyen Thi Thao",   "thao.marketing@hcl.com",    "0944444444"},
                {"Tran Van Tuan",     "tuan.operations@hcl.com",   "0955555551"},
                {"Le Thi Uyen",       "uyen.operations@hcl.com",   "0955555552"},
                {"Pham Van Vinh",     "vinh.operations@hcl.com",   "0955555553"},
                {"Hoang Thi Xuan",    "xuan.operations@hcl.com",   "0955555554"},
        };

        String[] staffIds = new String[20];
        for (int i = 0; i < 20; i++) {
            staffIds[i] = uuid();
            insertUser(staffIds[i], staffData[i][1], pw, staffData[i][0],
                    staffData[i][2], RoleEnum.STAFF, deptIds[i / 4],
                    now.minusDays(i));
        }

        // ── Documents ──────────────────────────────────────
        Object[][] docData = {
                {"Q1_Financial_Report.pdf",    DocumentTypeEnum.BALANCE_SHEET, DocumentFormatEnum.PDF,  4},
                {"Employment_Contract_An.pdf", DocumentTypeEnum.CONTRACT,      DocumentFormatEnum.PDF,  0},
                {"PaySlip_March_Bich.pdf",     DocumentTypeEnum.PAY_SLIP,      DocumentFormatEnum.PDF,  1},
                {"Marketing_Plan_Q2.docx",     DocumentTypeEnum.CONTRACT,      DocumentFormatEnum.WORD, 12},
                {"HR_Policy_2026.pdf",         DocumentTypeEnum.CONTRACT,      DocumentFormatEnum.PDF,  8},
                {"Balance_Sheet_Q1.csv",       DocumentTypeEnum.BALANCE_SHEET, DocumentFormatEnum.CSV,  5},
                {"Operations_Report.pdf",      DocumentTypeEnum.BALANCE_SHEET, DocumentFormatEnum.PDF,  16},
                {"Staff_Contract_Cuong.pdf",   DocumentTypeEnum.CONTRACT,      DocumentFormatEnum.PDF,  2},
                {"PaySlip_April_Dung.pdf",     DocumentTypeEnum.PAY_SLIP,      DocumentFormatEnum.PDF,  3},
                {"Finance_Summary.csv",        DocumentTypeEnum.BALANCE_SHEET, DocumentFormatEnum.CSV,  6},
                {"Recruitment_Plan.docx",      DocumentTypeEnum.CONTRACT,      DocumentFormatEnum.WORD, 9},
                {"PaySlip_March_Hoa.pdf",      DocumentTypeEnum.PAY_SLIP,      DocumentFormatEnum.PDF,  7},
                {"Campaign_Brief.docx",        DocumentTypeEnum.CONTRACT,      DocumentFormatEnum.WORD, 13},
                {"Payroll_Report_Q1.csv",      DocumentTypeEnum.BALANCE_SHEET, DocumentFormatEnum.CSV,  10},
                {"Vendor_Contract_2026.pdf",   DocumentTypeEnum.CONTRACT,      DocumentFormatEnum.PDF,  17},
                {"Performance_Review.docx",    DocumentTypeEnum.CONTRACT,      DocumentFormatEnum.WORD, 11},
                {"Social_Media_Plan.docx",     DocumentTypeEnum.CONTRACT,      DocumentFormatEnum.WORD, 14},
                {"Logistics_Report.pdf",       DocumentTypeEnum.BALANCE_SHEET, DocumentFormatEnum.PDF,  18},
                {"PaySlip_April_Son.pdf",      DocumentTypeEnum.PAY_SLIP,      DocumentFormatEnum.PDF,  15},
                {"Supply_Chain_Report.csv",    DocumentTypeEnum.BALANCE_SHEET, DocumentFormatEnum.CSV,  19},
        };

        String[] docIds = new String[20];
        for (int i = 0; i < docData.length; i++) {
            docIds[i] = uuid();
            int staffIdx = (int) docData[i][3];
            String uploaderDeptId = deptIds[staffIdx / 4];
            LocalDateTime uploaded = now.minusDays((int)(Math.random() * 10));

            em.createNativeQuery("""
                INSERT INTO documents
                  (id, name, document_link, type, format, size,
                   uploader_id, department_id, is_deleted, uploaded_date_time)
                VALUES (?,?,?,?,?,?,?,?,false,?)
                """)
                    .setParameter(1, docIds[i])
                    .setParameter(2, (String) docData[i][0])
                    .setParameter(3, "uploads/" + uuid() + "_" + docData[i][0])
                    .setParameter(4, ((DocumentTypeEnum) docData[i][1]).name())
                    .setParameter(5, ((DocumentFormatEnum) docData[i][2]).name())
                    .setParameter(6, (long)(50000 + Math.random() * 500000))
                    .setParameter(7, staffIds[staffIdx])
                    .setParameter(8, uploaderDeptId)
                    .setParameter(9, uploaded)
                    .executeUpdate();

            // ── Notification to boss ───────────────────────
            String bossId = bossIds[staffIdx / 4];
            em.createNativeQuery("""
                INSERT INTO notifications
                  (id, content, triggered_document_id, receiver_id,
                   has_read, is_read_date_time, created_at)
                VALUES (?,?,?,?,?,?,?)
                """)
                    .setParameter(1, uuid())
                    .setParameter(2, staffData[staffIdx][0] + " uploaded: " + docData[i][0])
                    .setParameter(3, docIds[i])
                    .setParameter(4, bossId)
                    .setParameter(5, i % 3 == 0)
                    .setParameter(6, i % 3 == 0 ? now.minusHours(1) : null)
                    .setParameter(7, now)
                    .executeUpdate();
        }
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