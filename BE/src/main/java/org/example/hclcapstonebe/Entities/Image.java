package org.example.hclcapstonebe.Entities;


import jakarta.persistence.*;
import lombok.*;
import org.example.hclcapstonebe.Enums.ImageFormatEnum;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "images")
@Getter @Setter @NoArgsConstructor @AllArgsConstructor @Builder
public class Image {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false, updatable = false)
    private LocalDateTime uploadedDateTime = LocalDateTime.now();

    private LocalDateTime latestViewedDateTime;

    @Column(nullable = false)
    private String imageLink;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private ImageFormatEnum format;

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
