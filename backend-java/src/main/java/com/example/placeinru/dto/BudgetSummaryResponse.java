package com.example.placeinru.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.util.Map;

@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class BudgetSummaryResponse {

    private Long tripId;
    private BigDecimal totalCost;
    private BigDecimal budgetLimit;
    private BigDecimal remainingBudget;
    private Boolean isOverBudget;
    private Map<String, BigDecimal> costByCategory;
}
