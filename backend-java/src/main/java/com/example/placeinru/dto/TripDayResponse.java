package com.example.placeinru.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class TripDayResponse {

    private Long id;
    private LocalDate date;
    private Integer dayNumber;
    @Builder.Default
    private List<RouteItemResponse> items = new ArrayList<>();
}
