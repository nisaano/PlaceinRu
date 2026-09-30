package com.example.placeinru.service;

import com.example.placeinru.config.JwtUtils;
import com.example.placeinru.dto.*;
import com.example.placeinru.entity.*;
import com.example.placeinru.exception.ResourceNotFoundException;
import com.example.placeinru.repository.RouteItemRepository;
import com.example.placeinru.repository.TripRepository;
import com.example.placeinru.repository.TripSpecification;
import com.example.placeinru.repository.UserRepository;
import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class TripService {

    private final TripRepository tripRepository;
    private final UserRepository userRepository;
    private final JwtUtils jwtUtils;
    private final RouteValidationService routeValidationService;
    private final TripBudgetService tripBudgetService;
    private final RouteItemRepository routeItemRepository;

    private User getUserByToken(String token) {
        if (token.startsWith("Bearer ")) {
            token = token.substring(7);
        }
        String email = jwtUtils.getEmailFromToken(token);
        return userRepository.findByEmail(email).orElseThrow(() -> new ResourceNotFoundException("Пользователь не найден"));
    }

    public TripResponse createTrip(TripCreateRequest request, String token) {
        User user = getUserByToken(token);

        Trip trip = Trip.builder()
                .userId(user.getId())
                .title(request.getTitle() != null ? request.getTitle() : "Поездка " + request.getDestination())
                .origin(request.getOrigin())
                .destination(request.getDestination())
                .startDate(request.getStartDate())
                .endDate(request.getEndDate())
                .budget(request.getBudget())
                .currency(request.getCurrency())
                .adults(request.getAdults())
                .children(request.getChildren())
                .tourismType(request.getTourismType())
                .transportType(request.getTransportType())
                .guideRequired(request.getGuideRequired())
                .guideId(request.getGuideId())
                .totalDistance(request.getTotalDistance())
                .fuelConsumption(request.getFuelConsumption())
                .fuelPrice(request.getFuelPrice())
                .tollRoadsCost(request.getTollRoadsCost())
                .build();

        if (request.getStartDate() != null && request.getEndDate() != null) {
            List<TripDay> days = new java.util.ArrayList<>();
            java.time.LocalDate currentDate = request.getStartDate();
            int dayNumber = 1;

            while (!currentDate.isAfter(request.getEndDate())) {
                TripDay day = TripDay.builder()
                        .trip(trip)
                        .date(currentDate)
                        .dayNumber(dayNumber++)
                        .build();
                days.add(day);
                currentDate = currentDate.plusDays(1);
            }
            trip.setDays(days);
        }
        Trip savedTrip = tripRepository.save(trip);
        return mapToResponse(savedTrip);
    }

    public List<TripResponse> getUserTrips(String token) {
        User user = getUserByToken(token);
        return tripRepository.findByUserIdOrderByIdDesc(user.getId()).stream()
                .map(this::mapToResponse)
                .toList();
    }

    public TripResponse getTripById(Long id, String token) {
        User user = getUserByToken(token);
        Trip trip = tripRepository.findByIdAndUserId(id, user.getId()).orElseThrow(() -> new ResourceNotFoundException("Поездка не найдена"));
        return mapToResponse(trip);
    }

    public void deleteTrip(Long id, String token) {
        User user = getUserByToken(token);
        Trip trip = tripRepository.findByIdAndUserId(id, user.getId()).orElseThrow(() -> new ResourceNotFoundException("Поездка не найдена"));
        tripRepository.delete(trip);
    }

    public TripResponse updateTrip(Long id, TripCreateRequest request, String token) {
        User user = getUserByToken(token);
        Trip trip = tripRepository.findByIdAndUserId(id, user.getId()).orElseThrow(() -> new ResourceNotFoundException("Поездка не найдена"));

        if (request.getTitle() != null) trip.setTitle(request.getTitle());
        if (request.getOrigin() != null) trip.setOrigin(request.getOrigin());
        if (request.getDestination() != null) trip.setDestination(request.getDestination());
        if (request.getStartDate() != null) trip.setStartDate(request.getStartDate());
        if (request.getEndDate() != null) trip.setEndDate(request.getEndDate());
        if (request.getBudget() != null) trip.setBudget(request.getBudget());
        if (request.getAdults() != null) trip.setAdults(request.getAdults());
        if (request.getChildren() != null) trip.setChildren(request.getChildren());
        if (request.getTourismType() != null) trip.setTourismType(request.getTourismType());
        if (request.getTransportType() != null) trip.setTransportType(request.getTransportType());
        if (request.getTotalDistance() != null) trip.setTotalDistance(request.getTotalDistance());
        if (request.getFuelConsumption() != null) trip.setFuelConsumption(request.getFuelConsumption());
        if (request.getFuelPrice() != null) trip.setFuelPrice(request.getFuelPrice());
        if (request.getTollRoadsCost() != null) trip.setTollRoadsCost(request.getTollRoadsCost());

        boolean datesChanged = false;
        if (request.getStartDate() != null && !request.getStartDate().equals(trip.getStartDate())) {
            trip.setStartDate(request.getStartDate());
            datesChanged = true;
        }

        if (request.getEndDate() != null && !request.getEndDate().equals(trip.getEndDate())) {
            trip.setEndDate(request.getEndDate());
            datesChanged = true;
        }

        if (datesChanged && trip.getStartDate() != null && trip.getEndDate() != null) {
            if (trip.getStartDate().isAfter(trip.getEndDate())) {
                throw new IllegalArgumentException("Дата начала поездки не может быть позже даты окончания");
            }

            if (trip.getDays() != null) {
                trip.getDays().clear();
            } else {
                trip.setDays(new java.util.ArrayList<>());
            }

            java.time.LocalDate currentDate = trip.getStartDate();
            int dayNumber = 1;
            while (!currentDate.isAfter(trip.getEndDate())) {
                TripDay day = TripDay.builder()
                        .trip(trip)
                        .date(currentDate)
                        .dayNumber(dayNumber++)
                        .build();
                trip.getDays().add(day);
                currentDate = currentDate.plusDays(1);
            }
        }

        Trip updatedTrip = tripRepository.save(trip);
        return mapToResponse(updatedTrip);
    }

    public Page<TripResponse> searchTrips(TripFilterRequest filter) {
        Sort sort = filter.getSortDirection().equalsIgnoreCase("ASC") ? Sort.by(filter.getSortBy()).ascending() : Sort.by(filter.getSortBy()).descending();
        Pageable pageable = PageRequest.of(filter.getPage(), filter.getSize(), sort);
        Page<Trip> tripPage = tripRepository.findAll(TripSpecification.filterTrips(filter), pageable);
        return tripPage.map(this::mapToResponse);
    }

    @Transactional
    public TripResponse updateTripStatus(Long id, TripStatus newStatus) {
        Trip trip = tripRepository.findById(id).orElseThrow(() -> new ResourceNotFoundException("Поездка не найдена"));
        String rawStatus = (trip.getStatus() != null) ? trip.getStatus().toUpperCase() : "DRAFT";
        TripStatus currentStatus = TripStatus.valueOf(rawStatus);

        if (!currentStatus.canTransitionTo(newStatus)) {
            throw new IllegalStateException("Нельзя перевести поездку из статуса " + currentStatus + " в " + newStatus);
        }

        if (newStatus == TripStatus.PLANNED) {
            boolean hasItems = trip.getDays() != null && trip.getDays().stream()
                    .anyMatch(day -> day.getItems() != null && !day.getItems().isEmpty());
            if (!hasItems) {
                throw new IllegalStateException("Нельзя перевести поездку в статус PLANNED без точек маршрута");
            }
        }

        trip.setStatus(newStatus.name().toUpperCase());
        Trip updatedTrip = tripRepository.save(trip);
        return mapToResponse(updatedTrip);
    }

    @Transactional
    public TripResponse assignGuide(Long tripId, AssignGuideRequest request) {
        Trip trip = tripRepository.findById(tripId).orElseThrow(() -> new ResourceNotFoundException("Поездка не найдена"));

        if (Boolean.FALSE.equals(trip.getGuideRequired())) {
            throw new IllegalStateException("Для данной поездки не требуется гид");
        }

        if (request.getGuideId() == null) {
            throw new IllegalArgumentException("ID гида не может быть пустым");
        }

        trip.setGuideId(request.getGuideId());
        Trip updatedTrip = tripRepository.save(trip);
        return mapToResponse(updatedTrip);
    }

    @Transactional
    public TripResponse removeGuide(Long tripId) {
        Trip trip = tripRepository.findById(tripId).orElseThrow(() -> new ResourceNotFoundException("Поездка не найдена"));
        trip.setGuideId(null);
        Trip updatedTrip = tripRepository.save(trip);
        return mapToResponse(updatedTrip);
    }

    @Transactional
    public TripResponse replaceRouteItem(Long tripId, Long itemId, RouteItemReplaceRequest request) {
        Trip trip = tripRepository.findById(tripId).orElseThrow(() -> new ResourceNotFoundException("Поездка с id " + tripId + " не найдена"));
        RouteItem item = routeItemRepository.findById(itemId).orElseThrow(() -> new ResourceNotFoundException("Элемент маршрута с id " + itemId + " не найден"));

        if (!item.getTripDay().getTrip().getId().equals(tripId)) {
            throw new IllegalArgumentException("Элемент маршрута не принадлежит указанной поездке");
        }

        if (request.getName() != null) item.setNotes(request.getName());
        if (request.getCategory() != null) item.setType(request.getCategory());
        if (request.getPrice() != null) item.setEstimatedCost(java.math.BigDecimal.valueOf(request.getPrice()));
        if (request.getDurationMinutes() != null) item.setDurationMinutes(request.getDurationMinutes());
        routeItemRepository.save(item);
        tripBudgetService.calculateBudget(trip.getId());

        RouteValidationResponse validation = routeValidationService.validateTripRoute(trip.getId());
        if (validation != null && Boolean.FALSE.equals(validation.getIsValid())) {
            String issuesText = (validation.getIssues() != null) ? validation.getIssues().stream()
                    .map(issue -> issue.getMessage() != null ? issue.getMessage() : issue.toString())
                    .collect(Collectors.joining(", ")) : "маршрут невалиден";
            throw new IllegalStateException("Замена точки приводит к ошибкам в маршруте: " + issuesText);
        }

        Trip updatedTrip = tripRepository.findById(tripId).orElseThrow(() -> new ResourceNotFoundException("Поездка не найдена"));

        return mapToResponse(updatedTrip);
    }

    @Transactional
    public TripResponse rebuildRoute(Long tripId) {
        Trip trip = tripRepository.findById(tripId).orElseThrow(() -> new ResourceNotFoundException("Поездка с id " + tripId + " не найдена"));

        RouteValidationResponse validation = routeValidationService.validateTripRoute(trip.getId());
        if (validation != null && Boolean.FALSE.equals(validation.getIsValid())) {
            String issuesText = (validation.getIssues() != null) ? validation.getIssues().stream()
                    .map(issue -> issue.getMessage() != null ? issue.getMessage() : issue.toString())
                    .collect(Collectors.joining(", ")) : "маршрут невалиден";
            throw new IllegalStateException("Маршрут содержит ошибки и не может быть перестроен: " + issuesText);
        }

        tripBudgetService.calculateBudget(trip.getId());

        Trip updatedTrip = tripRepository.findById(tripId).orElseThrow(() -> new ResourceNotFoundException("Поездка не найдена"));
        return mapToResponse(updatedTrip);
    }

    public TripResponse mapToResponse(Trip trip) {
        List<TripDayResponse> dayResponses = null;

        if (trip.getDays() != null) {
            dayResponses = trip.getDays().stream()
                    .map(day -> TripDayResponse.builder()
                            .id(day.getId())
                            .date(day.getDate())
                            .dayNumber(day.getDayNumber())
                            .items(day.getItems() != null ? day.getItems().stream()
                                    .map(item -> RouteItemResponse.builder()
                                            .id(item.getId())
                                            .dayId(day.getId())
                                            .type(item.getType())
                                            .objectId(item.getObjectId())
                                            .startTime(item.getStartTime())
                                            .endTime(item.getEndTime())
                                            .durationMinutes(item.getDurationMinutes())
                                            .order(item.getOrder())
                                            .estimatedCost(item.getEstimatedCost())
                                            .notes(item.getNotes())
                                            .build())
                                    .toList() : java.util.Collections.emptyList())
                            .build())
                    .toList();
        }

        return TripResponse.builder()
                .id(trip.getId())
                .userId(trip.getUserId())
                .title(trip.getTitle())
                .status(trip.getStatus())
                .origin(trip.getOrigin())
                .destination(trip.getDestination())
                .startDate(trip.getStartDate())
                .endDate(trip.getEndDate())
                .budget(trip.getBudget())
                .currency(trip.getCurrency())
                .adults(trip.getAdults())
                .children(trip.getChildren())
                .tourismType(trip.getTourismType())
                .transportType(trip.getTransportType())
                .guideRequired(trip.getGuideRequired())
                .guideId(trip.getGuideId())
                .createdAt(trip.getCreatedAt())
                .updatedAt(trip.getUpdatedAt())
                .days(dayResponses)
                .build();
    }
}
