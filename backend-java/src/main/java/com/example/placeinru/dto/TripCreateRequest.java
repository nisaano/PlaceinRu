package com.example.placeinru.dto;

import jakarta.validation.constraints.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;

@Data
public class TripCreateRequest {

    private String title;

    @NotBlank(message = "Укажите город отправления")
    private String origin;

    @NotBlank(message = "Укажите город назначения")
    private String destination;

    @NotNull(message = "Дата начала поездки обязательна")
    @FutureOrPresent(message = "Дата начала не может быть в прошлом")
    private LocalDate startDate;

    @NotNull(message = "Дата окончания поездки обязательна")
    private LocalDate endDate;

    @NotNull(message = "Укажите бюджет")
    @DecimalMin(value = "0.0", message = "Бюджет не может быть отрицательным")
    private BigDecimal budget;

    private String currency;

    @NotNull(message = "Укажите количество взрослых")
    @Min(value = 1, message = "Должен быть минимум 1 взрослый")
    private Integer adults;

    @Min(value = 0, message = "Количество детей не может быть отрицательным")
    private Integer children;


    private String tourismType;
    private String transportType;
    private Boolean guideRequired;
    private Long guideId;

    @PositiveOrZero(message = "Расстояние не может быть отрицательным")
    private Double totalDistance;

    @PositiveOrZero(message = "Расход топлива не может быть отрицательным")
    private Double fuelConsumption;

    @PositiveOrZero(message = "Цена топлива не может быть отрицательной")
    private Double fuelPrice;

    @PositiveOrZero(message = "Стоимость платных дорог не может быть отрицательной")
    private Double tollRoadsCost;
}
