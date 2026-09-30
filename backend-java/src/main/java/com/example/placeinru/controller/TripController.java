package com.example.placeinru.controller;

import com.example.placeinru.dto.*;
import com.example.placeinru.service.TripBudgetService;
import com.example.placeinru.service.TripService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/trips")
@RequiredArgsConstructor
@CrossOrigin(origins = "http://localhost:5173")
public class TripController {

    private final TripService tripService;
    private final TripBudgetService tripBudgetService;

    @PostMapping
    public ResponseEntity<TripResponse> createTrip(@Valid @RequestBody TripCreateRequest request, @RequestHeader("Authorization") String token) {
        return ResponseEntity.ok(tripService.createTrip(request, token));
    }

    @GetMapping
    public ResponseEntity<List<TripResponse>> getUserTrips(@RequestHeader("Authorization") String token) {
        return ResponseEntity.ok(tripService.getUserTrips(token));
    }

    @GetMapping("/{id}")
    public ResponseEntity<TripResponse> getTripById(@PathVariable Long id, @RequestHeader("Authorization") String token) {
        return ResponseEntity.ok(tripService.getTripById(id, token));
    }

    @PatchMapping("/{id}")
    public ResponseEntity<TripResponse> updateTrip(@PathVariable Long id, @Valid @RequestBody TripCreateRequest request, @RequestHeader("Authorization") String token) {
        return ResponseEntity.ok(tripService.updateTrip(id, request, token));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteTrip(@PathVariable Long id, @RequestHeader("Authorization") String token) {
        tripService.deleteTrip(id, token);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/{id}/budget")
    public ResponseEntity<BudgetSummaryResponse> getBudgetSummary(@PathVariable Long id) {
        return ResponseEntity.ok(tripBudgetService.calculateBudget(id));
    }

    @GetMapping("/search")
    public ResponseEntity<Page<TripResponse>> searchTrips(TripFilterRequest filter) {
        return ResponseEntity.ok(tripService.searchTrips(filter));
    }

    @PatchMapping("/{id}/status")
    public ResponseEntity<TripResponse> updatedStatus(@PathVariable Long id, @Valid @RequestBody TripStatusUpdateRequest request) {
        return ResponseEntity.ok(tripService.updateTripStatus(id, request.getStatus()));
    }

    @PutMapping("/{id}/guide")
    public ResponseEntity<TripResponse> assignGuide(@PathVariable Long id, @Valid @RequestBody AssignGuideRequest request) {
        return ResponseEntity.ok(tripService.assignGuide(id, request));
    }

    @DeleteMapping("/{id}/guide")
    public ResponseEntity<TripResponse> removeGuide(@PathVariable Long id) {
        return ResponseEntity.ok(tripService.removeGuide(id));
    }

    @PostMapping("/{id}/items/{itemId}/replace")
    public ResponseEntity<TripResponse> replaceRouteItem(@PathVariable Long id, @PathVariable Long itemId, @Valid @RequestBody RouteItemReplaceRequest request) {
        return ResponseEntity.ok(tripService.replaceRouteItem(id, itemId, request));
    }

    @PostMapping("/{id}/route/rebuild")
    public ResponseEntity<TripResponse> rebuildRoute(@PathVariable Long id) {
        return ResponseEntity.ok(tripService.rebuildRoute(id));
    }
}
