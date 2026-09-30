package com.example.placeinru.repository;

import com.example.placeinru.entity.RouteItem;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface RouteItemRepository extends JpaRepository<RouteItem, Long> {
    List<RouteItem> findByTripDayIdOrderByOrderAsc(Long dayId);
}
