package com.example.placeinru.service;

import com.example.placeinru.dto.BudgetSummaryResponse;
import com.example.placeinru.entity.RouteItem;
import com.example.placeinru.entity.Trip;
import com.example.placeinru.entity.TripDay;
import com.example.placeinru.repository.TripRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class TripBudgetService {

    private final TripRepository tripRepository;

    public BudgetSummaryResponse calculateBudget(Long tripId) {
        Trip trip = tripRepository.findById(tripId).orElseThrow(() -> new RuntimeException("Поездка не найдена"));
        BigDecimal totalCost = BigDecimal.ZERO;
        Map<String, BigDecimal> costByCategory = new HashMap<>();

        costByCategory.put("HOTEL", BigDecimal.ZERO);
        costByCategory.put("TRANSPORT", BigDecimal.ZERO);
        costByCategory.put("RESTAURANT", BigDecimal.ZERO);
        costByCategory.put("ATTRACTION", BigDecimal.ZERO);
        costByCategory.put("GUIDE", BigDecimal.ZERO);

        if (trip.getDays() != null) {
            for (TripDay day : trip.getDays()) {
                if (day.getItems() != null) {
                    for (RouteItem item : day.getItems()) {
                        if (item.getEstimatedCost() != null) {
                            BigDecimal itemCost = item.getEstimatedCost();
                            totalCost = totalCost.add(itemCost);
                            String category = item.getType() != null ? item.getType().toUpperCase() : "OTHER";
                            costByCategory.put(category, costByCategory.getOrDefault(category, BigDecimal.ZERO).add(itemCost));
                        }
                    }
                }
            }
        }

        if ("CAR".equalsIgnoreCase(trip.getTransportType())) {
            double distance = trip.getTotalDistance() != null ? trip.getTotalDistance() : 0.0;
            double consumption = trip.getFuelConsumption() != null ? trip.getFuelConsumption() : 0.0;
            double price = trip.getFuelPrice() != null ? trip.getFuelPrice() : 0.0;
            double tolls = trip.getTollRoadsCost() != null ? trip.getTollRoadsCost() : 0.0;

            double fuelCost = (distance / 100.0) * consumption * price;
            BigDecimal carTransportCost = BigDecimal.valueOf(fuelCost + tolls);

            totalCost = totalCost.add(carTransportCost);
            BigDecimal currentTransportCost = costByCategory.getOrDefault("TRANSPORT", BigDecimal.ZERO);
            costByCategory.put("TRANSPORT", currentTransportCost.add(carTransportCost));
        }

        BigDecimal budgetLimit = trip.getBudget() != null ? trip.getBudget() : BigDecimal.ZERO;
        BigDecimal remainingBudget = budgetLimit.subtract(totalCost);
        boolean isOverBudget = remainingBudget.compareTo(BigDecimal.ZERO) < 0;

        return BudgetSummaryResponse.builder()
                .tripId(trip.getId())
                .totalCost(totalCost)
                .budgetLimit(budgetLimit)
                .remainingBudget(remainingBudget)
                .isOverBudget(isOverBudget)
                .costByCategory(costByCategory)
                .build();
    }
}
