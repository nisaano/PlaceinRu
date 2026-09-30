package com.example.placeinru.service;

import com.example.placeinru.dto.RouteValidationResponse;
import com.example.placeinru.dto.ValidationIssue;
import com.example.placeinru.entity.RouteItem;
import com.example.placeinru.entity.Trip;
import com.example.placeinru.entity.TripDay;
import com.example.placeinru.repository.TripRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.LocalTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

@Service
@RequiredArgsConstructor
public class RouteValidationService {

    private final TripRepository tripRepository;

    public RouteValidationResponse validateTripRoute(Long tripId) {
        Trip trip = tripRepository.findById(tripId).orElseThrow(() -> new RuntimeException("Поездка не найдена"));

        List<ValidationIssue> issues = new ArrayList<>();

        if (trip.getDays() != null) {
            for (TripDay day : trip.getDays()) {
                if (day.getItems() != null && !day.getItems().isEmpty()) {
                    List<RouteItem> sortedItems = day.getItems().stream()
                            .sorted(Comparator.comparing(item -> item.getStartTime() != null ? item.getStartTime() : LocalTime.MIN)).toList();
                    RouteItem previousItem = null;

                    for (RouteItem currentItem : sortedItems) {
                        if (currentItem.getStartTime() != null && currentItem.getEndTime() != null) {
                            if (currentItem.getStartTime().isAfter(currentItem.getEndTime())) {
                                issues.add(ValidationIssue.builder()
                                        .dayId(day.getId())
                                        .dayNumber(day.getDayNumber())
                                        .itemId(currentItem.getId())
                                        .type("INVALID_TIME_RANGE")
                                        .message("Время начала (" + currentItem.getStartTime() +
                                                ") не может быть позже времени окончания (" + currentItem.getEndTime() + ")")
                                        .build());
                            }
                        }

                        if (previousItem != null && previousItem.getEndTime() != null && currentItem.getStartTime() != null) {

                            int travelTime = currentItem.getTravelTimeFromPreviousMinutes() != null ? currentItem.getTravelTimeFromPreviousMinutes() : 0;
                            LocalTime minimumAllowedStartTime = previousItem.getEndTime().plusMinutes(travelTime);

                            if (currentItem.getStartTime().isBefore(previousItem.getEndTime())) {
                                issues.add(ValidationIssue.builder()
                                        .dayId(day.getId())
                                        .dayNumber(day.getDayNumber())
                                        .itemId(currentItem.getId())
                                        .type("OVERLAP")
                                        .message("Наложение по времени с предыдущей точкой. Начало в " +
                                                currentItem.getStartTime() + ", но предыдущее место заканчивается в " + previousItem.getEndTime())
                                        .build());
                            } else if (currentItem.getStartTime().isBefore(minimumAllowedStartTime)) {
                                issues.add(ValidationIssue.builder()
                                        .dayId(day.getId())
                                        .dayNumber(day.getDayNumber())
                                        .itemId(currentItem.getId())
                                        .type("INSUFFICIENT_TRAVEL_TIME")
                                        .message("Недостаточно времени на дорогу (" + travelTime + " мин.). Рекомендуемое время выезда: не ранее " + minimumAllowedStartTime)
                                        .build());
                            }
                        }
                        previousItem = currentItem;
                    }
                }
            }
        }
        return RouteValidationResponse.builder()
                .tripId(tripId)
                .isValid(issues.isEmpty())
                .issues(issues)
                .build();
    }
}
