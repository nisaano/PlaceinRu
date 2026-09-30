package com.example.placeinru.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class RegisterRequest {

    @NotBlank(message = "Email обязателен")
    @Email(message = "Некорректный формат email")
    private String email;

    @NotBlank(message = "Пароль обязателен")
    @Size(min = 6, max = 20, message = "Пароль должен содержать от 6 до 20 символов")
    private String password;

    @NotBlank(message = "Имя обязательно")
    @Size(min = 3, max = 10, message = "Имя должно быть от 3 до 10 символов")
    private String name;
}
