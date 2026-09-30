package com.example.placeinru.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalTime;

@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class RouteItemResponse {

    private Long id;
    private Long dayId;
    private String type;
    private String objectId;
    private LocalTime startTime;
    private LocalTime endTime;
    private Integer durationMinutes;
    private Integer order;
    private BigDecimal estimatedCost;
    private String notes;
}
