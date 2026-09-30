package com.example.placeinru.repository;

import com.example.placeinru.entity.Trip;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface TripRepository extends JpaRepository<Trip, Long>, JpaSpecificationExecutor<Trip> {
    List<Trip> findByUserIdOrderByIdDesc(Long userId);
    Optional<Trip> findByIdAndUserId(Long id, Long userId);
}
