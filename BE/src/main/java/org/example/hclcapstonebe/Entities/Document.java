package org.example.hclcapstonebe.Entities;

import jakarta.persistence.*;
import lombok.*;
import org.example.hclcapstonebe.Enums.DocumentFormatEnum;
import org.example.hclcapstonebe.Enums.DocumentTypeEnum;
import org.example.hclcapstonebe.Enums.RedactedPreviewStatus;
import org.example.hclcapstonebe.Enums.ScanStatus;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "documents")
@Getter @Setter @NoArgsConstructor @AllArgsConstructor @Builder
public class Document {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false)
    private String name;

    @CreationTimestamp
    @Column(nullable = false, updatable = false)
    private LocalDateTime uploadedDateTime;

    private LocalDateTime latestViewedDateTime;

    @Column(nullable = false)
    private String documentLink;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private DocumentTypeEnum type;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private DocumentFormatEnum format;

    private Long byteSize; // bytes

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "uploader_id", nullable = false)
    private User uploader;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "department_id", nullable = false)
    private Department department;

    @Column(nullable = false)
    @Builder.Default
    private boolean isDeleted = false;

    private LocalDateTime deletedAt;

    @Enumerated(EnumType.STRING)
    @Column(name = "scan_status")
    private ScanStatus scanStatus;

    private String scanMessage;

    private LocalDateTime scannedAt;

    @Column(nullable = false)
    @Builder.Default
    private boolean aiProcessed = false;

    // Issue #222 -- AI processing failure (e.g. a RestTemplate read timeout
    // on AI's synchronous /process call) used to leave aiProcessed silently
    // false forever, with no way for the uploader or anyone else to tell
    // "still processing" apart from "permanently stuck." Set alongside
    // aiProcessed=false in AiProcessingService's own catch block -- the
    // same code path that already reliably observes the failure, no
    // separate polling/reconciliation job needed.
    @Column(nullable = false)
    @Builder.Default
    private boolean aiProcessingFailed = false;

    @Column(length = 500)
    private String aiFailureReason;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    private String aiResult;

    // No @Column(nullable = false) / @Builder.Default here deliberately --
    // existing rows will have NULL after the schema updates (ddl-auto=update
    // adds the column but doesn't backfill existing rows), so every read
    // site must treat null the same as NOT_STARTED rather than relying on a
    // DB-level default.
    @Enumerated(EnumType.STRING)
    private RedactedPreviewStatus redactedPreviewStatus;

    private String redactedPreviewPath;

    @Column(length = 500)
    private String redactedPreviewFailureReason;

    private BigDecimal proposedRepaymentAmount;
}
