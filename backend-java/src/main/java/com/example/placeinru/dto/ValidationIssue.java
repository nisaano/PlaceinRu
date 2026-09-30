package com.example.placeinru.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class ValidationIssue {

    private Long dayId;
    private Integer dayNumber;
    private Long itemId;
    private String type;
    private String message;
}
