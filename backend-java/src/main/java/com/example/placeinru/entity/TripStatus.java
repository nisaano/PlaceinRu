package com.example.placeinru.entity;

public enum TripStatus {

    DRAFT,
    PLANNED,
    IN_PROGRESS,
    COMPLETED,
    CANCELLED;

    public boolean canTransitionTo(TripStatus newStatus) {
        return switch (this) {
            case DRAFT -> newStatus == PLANNED || newStatus == CANCELLED;
            case PLANNED -> newStatus == IN_PROGRESS || newStatus == CANCELLED;
            case IN_PROGRESS -> newStatus == COMPLETED || newStatus == CANCELLED;
            case COMPLETED, CANCELLED -> false;
        };
    }
}
