# 🚀 PlaceinRu — Java Backend Service

Основной микросервис бизнес-логики, аутентификации, планирования путешествий, валидации маршрутов и финансового расчёта для туристической платформы **PlaceinRu**.

---

## 🛠 Технологический стек

* **Язык программирования:** Java 17+
* **Фреймворк:** Spring Boot 3.x (Spring Web, Spring Data JPA, Spring Security)
* **Безопасность:** JWT (JSON Web Tokens) + BCrypt
* **База данных:** PostgreSQL
* **Документация API:** Springdoc OpenAPI / Swagger UI
* **Инструменты сборки и вспомогательные библиотеки:** Maven, Lombok

---

## 📋 Основной функционал сервиса

1. **🔐 Аутентификация и авторизация (`AuthService`)**

   * Регистрация пользователей с хешированием паролей (BCrypt).
   * Выдача двух токенов: `Access Token` и `Refresh Token`.
   * Получение профиля текущего пользователя (`/api/v1/auth/me`).

2. **🧳 Управление поездками (`TripService`)**

   * Создание, просмотр, обновление и удаление поездок (CRUD).
   * Автоматическая генерация дней поездки (`TripDay`) при указании дат.
   * Управление точками маршрута (`RouteItem`): замена, удаление, перестройка.
   * Фильтрация и пагинация списков поездок (`TripSpecification`).

3. **📐 Движок валидации маршрутов (`RouteValidationService`)**

   * Автоматическая проверка корректности временных интервалов (время начала не может быть позже времени окончания).
   * Обнаружение наложений (пересечений) посещаемых мест по времени.
   * Проверка запаса времени на перемещение между локациями (`travelTimeFromPreviousMinutes`).

4. **💰 Финансовый калькулятор бюджета (`TripBudgetService`)**

   * Расчёт полной стоимости поездки с разбивкой по категориям (`HOTEL`, `TRANSPORT`, `RESTAURANT`, `ATTRACTION`, `GUIDE`).
   * Учёт расходов на автомобиль: расчёт топлива по расстоянию, среднему расходу и цене бензина, а также платных дорог.
   * Отслеживание превышения установленного лимита бюджета.

5. **🧭 Модуль гидов**

   * Запрос, назначение и открепление гида от конкретной поездки.

---

## 📁 Структура проекта

```text
backend-java/
├── src/
│   ├── main/
│   │   ├── java/com/example/placeinru/
│   │   │   ├── config/         # Настройки Spring Security, JWT и Swagger
│   │   │   ├── controller/     # REST-контроллеры API
│   │   │   ├── dto/            # Data Transfer Objects (запросы и ответы)
│   │   │   ├── entity/         # JPA-сущности БД (User, Trip, TripDay, RouteItem)
│   │   │   ├── exception/      # Глобальная обработка ошибок и исключений
│   │   │   ├── repository/     # Spring Data JPA-репозитории
│   │   │   └── service/        # Сервисный слой бизнес-логики
│   │   └── resources/
│   │       └── application.properties # Конфигурация приложения
└── pom.xml                     # Спецификация зависимостей Maven
```

---

## ⚙️ Переменные окружения

Перед запуском приложения необходимо задать следующие переменные окружения:

```env
DB_URL=jdbc:postgresql://localhost:5432/placeinru_db
DB_USERNAME=postgres
DB_PASSWORD=your_database_password_here

JWT_SECRET=your_long_secret_string_here
JWT_EXPIRATION=86400000
JWT_REFRESH_EXPIRATION=604800000
```

> ⚠️ Не храните реальные пароли и `JWT_SECRET` в репозитории. Для локальной разработки используйте переменные окружения или `.env`-файл, добавленный в `.gitignore`.

---

## 🚀 Локальный запуск проекта

### Требования

* JDK 17 или выше
* PostgreSQL
* Maven

### 1. Создание базы данных

Подключитесь к PostgreSQL и выполните:

```sql
CREATE DATABASE placeinru_db;
```

### 2. Переход в директорию проекта

```bash
cd backend-java
```

### 3. Настройка переменных окружения

#### PowerShell (Windows)

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/placeinru_db"
$env:DB_USERNAME="postgres"
$env:DB_PASSWORD="your_postgres_password"
$env:JWT_SECRET="your_long_secret_string_here"
$env:JWT_EXPIRATION="86400000"
$env:JWT_REFRESH_EXPIRATION="604800000"
```

#### CMD (Windows)

```cmd
set DB_URL=jdbc:postgresql://localhost:5432/placeinru_db
set DB_USERNAME=postgres
set DB_PASSWORD=your_postgres_password
set JWT_SECRET=your_long_secret_string_here
set JWT_EXPIRATION=86400000
set JWT_REFRESH_EXPIRATION=604800000
```

### 4. Запуск приложения

```bash
mvn spring-boot:run
```

После успешного запуска сервер будет доступен по адресу:

http://localhost:8080

---

## 📖 Документация API

После запуска приложения документация OpenAPI доступна по следующим адресам:

* **Swagger UI:** http://localhost:8080/swagger-ui.html
* **OpenAPI Schema (JSON):** http://localhost:8080/v3/api-docs

---

## 🔑 API Authentication

Для защищённых эндпоинтов используется JWT-аутентификация.

После авторизации необходимо передавать access token в HTTP-заголовке:

```http
Authorization: Bearer <access_token>
```

---

## 🗄️ База данных

Проект использует **PostgreSQL** в качестве основной базы данных.

Параметры подключения задаются через переменные окружения:

```text
DB_URL
DB_USERNAME
DB_PASSWORD
```

---

## 🏗️ Сборка проекта

Для сборки проекта без запуска приложения:

```bash
mvn clean package
```

После успешной сборки JAR-файл будет создан в директории:

```text
target/
```

Запуск собранного приложения:

```bash
java -jar target/<application-name>.jar
```

---

## 🧪 Тестирование

Для запуска тестов используйте:

```bash
mvn test
```

---
