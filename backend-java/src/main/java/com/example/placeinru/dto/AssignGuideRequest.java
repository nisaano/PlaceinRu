package com.example.placeinru.dto;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class AssignGuideRequest {

    @NotNull(message = "ID гида обязателен")
    @Positive(message = "ID гида должен быть положительным числом")
    private Long guideId;
}
