package com.example.placeinru.dto;

import com.example.placeinru.entity.TripStatus;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class TripStatusUpdateRequest {

    @NotNull(message = "Новый статус обязателен")
    private TripStatus status;
}
