package org.example.hclcapstonebe.Entities;

import jakarta.persistence.*;
import lombok.*;
import org.example.hclcapstonebe.Enums.DocumentFormatEnum;
import org.example.hclcapstonebe.Enums.DocumentTypeEnum;
import org.example.hclcapstonebe.Enums.ScanStatus;
import org.hibernate.annotations.CreationTimestamp;

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
    private boolean isDeleted = false;

    private LocalDateTime deletedAt;

    @Enumerated(EnumType.STRING)
    @Column(name = "scan_status")
    private ScanStatus scanStatus;

    private String scanMessage;

    private LocalDateTime scannedAt;
}
