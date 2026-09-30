package com.example.placeinru.dto;

import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.PositiveOrZero;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class RouteItemReplaceRequest {

    private String name;
    private String category;

    @PositiveOrZero(message = "Цена не может быть отрицательной")
    private Double price;

    @Positive(message = "Длительность должна быть больше 0 минут")
    private Integer durationMinutes;

    private Long regionId;
}
