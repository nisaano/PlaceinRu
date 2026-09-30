package com.example.placeinru.controller;

import com.example.placeinru.dto.BudgetSummaryResponse;
import com.example.placeinru.dto.RouteItemCreateRequest;
import com.example.placeinru.dto.RouteItemResponse;
import com.example.placeinru.dto.RouteValidationResponse;
import com.example.placeinru.service.RouteItemService;
import com.example.placeinru.service.RouteValidationService;
import com.example.placeinru.service.TripBudgetService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/trips")
@RequiredArgsConstructor
@CrossOrigin(origins = "http://localhost:5173")
public class RouteItemController {

    private final RouteItemService routeItemService;
    private final TripBudgetService tripBudgetService;
    private final RouteValidationService routeValidationService;

    @PostMapping("/items")
    public ResponseEntity<RouteItemResponse> addItem(@Valid @RequestBody RouteItemCreateRequest request) {
        return ResponseEntity.ok(routeItemService.addItemToDay(request));
    }

    @GetMapping("/{id}/validate")
    public ResponseEntity<RouteValidationResponse> validateRoute(@PathVariable Long id) {
        return ResponseEntity.ok(routeValidationService.validateTripRoute(id));
    }
}
