package com.example.placeinru.entity;


import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "trips")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Trip {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    private String title;
    private String status;
    private String origin;
    private String destination;

    private LocalDate startDate;
    private LocalDate endDate;

    private BigDecimal budget;
    private String currency;

    private Integer adults;
    private Integer children;

    private String tourismType;

    private Boolean guideRequired;
    private Long guideId;

    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    @Column(name = "transport_type")
    private String transportType;

    @Column(name = "total_distance")
    private Double totalDistance;

    @Column(name = "fuel_consumption")
    private Double fuelConsumption;

    @Column(name = "fuel_price")
    private Double fuelPrice;

    @Column(name = "toll_roads_cost")
    private Double tollRoadsCost;

    @OneToMany(mappedBy = "trip", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private List<TripDay> days = new ArrayList<>();

    @PrePersist
    protected void onCreate() {
        this.createdAt = LocalDateTime.now();
        this.updatedAt = LocalDateTime.now();
        if (this.currency == null) this.currency = "RUB";
        if (this.status == null) this.status = "draft";
    }

    @PreUpdate
    protected void onUpdate() {
        this.updatedAt = LocalDateTime.now();
    }
}
