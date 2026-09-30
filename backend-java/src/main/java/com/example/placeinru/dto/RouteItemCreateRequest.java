package com.example.placeinru.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalTime;

@Data
public class RouteItemCreateRequest {

    private Long dayId;
    private String type;
    private String objectId;
    private LocalTime startTime;
    private LocalTime endTime;
    private Integer durationMinutes;
    private Integer order;
    private Double latitude;
    private Double longitude;
    private BigDecimal estimatedCost;
    private Integer travelTimeFromPreviousMinutes;
    private String notes;
}
