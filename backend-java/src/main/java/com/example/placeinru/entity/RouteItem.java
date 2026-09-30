package com.example.placeinru.entity;

import jakarta.persistence.*;
import lombok.*;

import java.math.BigDecimal;
import java.time.LocalTime;

@Entity
@Table(name = "route_items")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class RouteItem {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "day_id", nullable = false)
    @ToString.Exclude
    private TripDay tripDay;

    private String type;
    private String objectId;

    private LocalTime startTime;
    private LocalTime endTime;
    private Integer durationMinutes;

    @Column(name = "item_order")
    private Integer order;

    private Double latitude;
    private Double longitude;

    private BigDecimal estimatedCost;
    private Integer travelTimeFromPreviousMinutes;

    private String notes;
}
