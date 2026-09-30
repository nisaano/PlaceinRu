package com.example.placeinru.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class TripResponse {

    private Long id;
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
    private String transportType;
    private Boolean guideRequired;
    private Long guideId;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private List<TripDayResponse> days;
}
