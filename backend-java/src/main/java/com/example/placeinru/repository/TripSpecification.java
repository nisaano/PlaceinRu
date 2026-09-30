package com.example.placeinru.repository;

import com.example.placeinru.dto.TripFilterRequest;
import com.example.placeinru.entity.Trip;
import jakarta.persistence.criteria.Predicate;
import org.springframework.data.jpa.domain.Specification;

import java.util.ArrayList;
import java.util.List;

public class TripSpecification {

    public static Specification<Trip> filterTrips(TripFilterRequest filter) {
        return (root, query, criteriaBuilder) -> {
            List<Predicate> predicates = new ArrayList<>();

            if (filter.getDestination() != null && !filter.getDestination().isBlank()) {
                predicates.add(criteriaBuilder.like(criteriaBuilder.lower(root.get("destination")), "%" + filter.getDestination().toLowerCase() + "%"));
            }

            if (filter.getStatus() != null && !filter.getStatus().isBlank()) {
                predicates.add(criteriaBuilder.equal(root.get("status"), filter.getStatus()));
            }

            if (filter.getMinBudget() != null) {
                predicates.add(criteriaBuilder.greaterThanOrEqualTo(root.get("budget"), filter.getMinBudget()));
            }

            if (filter.getMaxBudget() != null) {
                predicates.add(criteriaBuilder.lessThanOrEqualTo(root.get("budget"), filter.getMaxBudget()));
            }

            if (filter.getStartDateFrom() != null) {
                predicates.add(criteriaBuilder.greaterThanOrEqualTo(root.get("startDate"), filter.getStartDateFrom()));
            }

            if (filter.getEndDateTo() != null) {
                predicates.add(criteriaBuilder.lessThanOrEqualTo(root.get("endDate"), filter.getEndDateTo()));
            }

            return criteriaBuilder.and(predicates.toArray(new Predicate[0]));
        };
    }
}
