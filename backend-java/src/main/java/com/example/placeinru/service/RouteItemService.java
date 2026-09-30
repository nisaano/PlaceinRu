package com.example.placeinru.service;

import com.example.placeinru.dto.RouteItemCreateRequest;
import com.example.placeinru.dto.RouteItemResponse;
import com.example.placeinru.entity.RouteItem;
import com.example.placeinru.entity.TripDay;
import com.example.placeinru.repository.RouteItemRepository;
import com.example.placeinru.repository.TripDayRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class RouteItemService {

    private final RouteItemRepository routeItemRepository;
    private final TripDayRepository tripDayRepository;

    public RouteItemResponse addItemToDay(RouteItemCreateRequest request) {
        TripDay day = tripDayRepository.findById(request.getDayId()).orElseThrow(() -> new RuntimeException("День поездки не найден"));

        RouteItem item = RouteItem.builder()
                .tripDay(day)
                .type(request.getType())
                .objectId(request.getObjectId())
                .startTime(request.getStartTime())
                .endTime(request.getEndTime())
                .durationMinutes(request.getDurationMinutes())
                .order(request.getOrder())
                .latitude(request.getLatitude())
                .longitude(request.getLongitude())
                .estimatedCost(request.getEstimatedCost())
                .travelTimeFromPreviousMinutes(request.getTravelTimeFromPreviousMinutes())
                .notes(request.getNotes())
                .build();

        RouteItem savedItem = routeItemRepository.save(item);

        return RouteItemResponse.builder()
                .id(savedItem.getId())
                .dayId(day.getId())
                .type(savedItem.getType())
                .objectId(savedItem.getObjectId())
                .startTime(savedItem.getStartTime())
                .endTime(savedItem.getEndTime())
                .durationMinutes(savedItem.getDurationMinutes())
                .order(savedItem.getOrder())
                .estimatedCost(savedItem.getEstimatedCost())
                .notes(savedItem.getNotes())
                .build();
    }
}
