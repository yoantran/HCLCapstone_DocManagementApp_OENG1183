package org.example.hclcapstonebe.Entities;


import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "departments")
@Getter @Setter @NoArgsConstructor @AllArgsConstructor @Builder
public class Department {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private String id;

    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAtDateTime = LocalDateTime.now();

    @Column(nullable = false)
    private String name;

    // Boss is a User — cannot be null (must assign 1 boss)
    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "boss_id", nullable = false)
    private User boss;
}