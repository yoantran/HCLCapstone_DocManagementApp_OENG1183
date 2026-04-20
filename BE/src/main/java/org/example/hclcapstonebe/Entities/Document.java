package org.example.hclcapstonebe.Entities;

import jakarta.persistence.*;
import lombok.*;
import org.example.hclcapstonebe.Enums.DocumentFormatEnum;
import org.example.hclcapstonebe.Enums.DocumentTypeEnum;

import java.time.LocalDateTime;

@Entity
@Table(name = "documents")
@Getter @Setter @NoArgsConstructor @AllArgsConstructor @Builder
public class Document {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private String id;

    @Column(nullable = false)
    private String name;

    @Column(nullable = false, updatable = false)
    private LocalDateTime uploadedDateTime = LocalDateTime.now();

    private LocalDateTime latestViewedDateTime;

    @Column(nullable = false)
    private String documentLink;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private DocumentTypeEnum type;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private DocumentFormatEnum format;

    private Long size; // bytes

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "uploader_id", nullable = false)
    private User uploader;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "department_id", nullable = false)
    private Department department;

    @Column(nullable = false)
    private boolean isDeleted = false;

    private LocalDateTime deletedAt;
}
