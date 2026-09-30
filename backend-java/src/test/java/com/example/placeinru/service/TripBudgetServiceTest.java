package com.example.placeinru.service;

import com.example.placeinru.dto.BudgetSummaryResponse;
import com.example.placeinru.entity.RouteItem;
import com.example.placeinru.entity.Trip;
import com.example.placeinru.entity.TripDay;
import com.example.placeinru.repository.TripRepository;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
public class TripBudgetServiceTest {

    @Mock
    private TripRepository tripRepository;

    @InjectMocks
    private TripBudgetService tripBudgetService;

    @Test
    @DisplayName("Расчёт бюджета для авто с точками маршрута (Бензин + Платные дороги + Отели)")
    void calculateBudget_CarTripWithItems_Success() {

        Long tripId = 1L;

        RouteItem hotelItem = RouteItem.builder()
                .type("HOTEL")
                .estimatedCost(BigDecimal.valueOf(5000))
                .build();

        TripDay day = TripDay.builder()
                .items(List.of(hotelItem))
                .build();

        Trip trip = Trip.builder()
                .id(tripId)
                .budget(BigDecimal.valueOf(20000))
                .transportType("CAR")
                .totalDistance(1000.0)
                .fuelConsumption(10.0)
                .fuelPrice(60.0)
                .tollRoadsCost(1500.0)
                .days(List.of(day))
                .build();

        when(tripRepository.findById(tripId)).thenReturn(Optional.of(trip));

        BudgetSummaryResponse response = tripBudgetService.calculateBudget(tripId);

        assertNotNull(response);
        assertEquals(BigDecimal.valueOf(12500.0), response.getTotalCost());
        assertEquals(BigDecimal.valueOf(7500.0), response.getRemainingBudget());
        assertFalse(response.getIsOverBudget());
        assertEquals(BigDecimal.valueOf(7500.0), response.getCostByCategory().get("TRANSPORT"));
    }

    @Test
    @DisplayName("Флаг isOverBudget должен возвращать true при превышении лимита")
    void calculateBudget_ExceedsBudget_SetsOverBudgetTrue() {

        Long tripId = 2L;

        Trip trip = Trip.builder()
                .id(tripId)
                .budget(BigDecimal.valueOf(5000))
                .transportType("CAR")
                .totalDistance(1000.0)
                .fuelConsumption(10.0)
                .fuelPrice(60.0)
                .build();

        when(tripRepository.findById(tripId)).thenReturn(Optional.of(trip));

        BudgetSummaryResponse response = tripBudgetService.calculateBudget(tripId);

        assertTrue(response.getIsOverBudget());
        assertTrue(response.getRemainingBudget().compareTo(BigDecimal.ZERO) < 0);
    }
}
