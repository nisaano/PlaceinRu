package com.example.placeinru.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class RouteValidationResponse {

    private Long tripId;
    private Boolean isValid;
    private List<ValidationIssue> issues;
}
