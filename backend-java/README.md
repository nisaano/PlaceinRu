# 🚀 PlaceinRu — Java Backend

Java backend-сервис туристической платформы **PlaceinRu**.

Основная ответственность сервиса — аутентификация пользователей, управление поездками, работа с маршрутами, валидация маршрутов, расчёт бюджета и работа с гидами.

---

## 🛠 Технологический стек

* Java 17+
* Spring Boot 3
* Spring Web
* Spring Data JPA / Hibernate
* Spring Security + JWT
* BCrypt
* PostgreSQL
* Maven
* Lombok
* Springdoc OpenAPI / Swagger UI

---

## 📋 Основной функционал

### Аутентификация

* Регистрация и авторизация пользователей.
* JWT Access / Refresh Token.
* Получение текущего пользователя.

### Поездки

* Создание и редактирование поездок.
* Получение списка поездок.
* Удаление поездок.
* Пагинация и фильтрация.
* Автоматическое создание дней поездки.

### Маршруты

* Получение маршрута по дням.
* Добавление и удаление точек.
* Изменение элементов маршрута.
* Замена отдельных элементов.
* Полная перестройка маршрута.

### Валидация

`RouteValidationService` проверяет:

* даты и время посещений;
* длительность;
* пересечения временных интервалов;
* время перемещения между точками;
* расстояния и последовательность маршрута;
* доступность объектов;
* возможность выполнения маршрута.

### Бюджет

`TripBudgetService` рассчитывает общую стоимость поездки:

* отели;
* транспорт;
* рестораны;
* достопримечательности;
* гид;
* автомобиль;
* топливо;
* платные дороги.

Также учитывается установленный пользователем бюджет.

### Гиды

* Работа с каталогом гидов.
* Назначение гида на поездку.
* Открепление гида.

---

## 📁 Структура проекта

```text
backend-java/
├── src/
│   ├── main/
│   │   ├── java/com/example/placeinru/
│   │   │   ├── config/
│   │   │   ├── controller/
│   │   │   ├── dto/
│   │   │   ├── entity/
│   │   │   ├── exception/
│   │   │   ├── repository/
│   │   │   └── service/
│   │   └── resources/
│   │       └── application.properties
│   └── test/
└── pom.xml
```

---

## 🔗 Основные API

### Auth

```text
POST   /auth/register
POST   /auth/login
POST   /auth/refresh
GET    /auth/me
```

### Trips

```text
POST   /trips
GET    /trips
GET    /trips/{id}
PATCH  /trips/{id}
DELETE /trips/{id}
```

### Route

```text
GET   /trips/{id}/route
POST  /trips/{id}/route/rebuild
PATCH /trips/{id}/route
```

### Route Items

```text
POST   /trips/{id}/items
PATCH  /trips/{id}/items/{item_id}
DELETE /trips/{id}/items/{item_id}
POST   /trips/{id}/items/{item_id}/replace
```

---

## ⚙️ Переменные окружения

```env
DB_URL=jdbc:postgresql://localhost:5432/placeinru_db
DB_USERNAME=postgres
DB_PASSWORD=your_database_password

JWT_SECRET=your_secret
JWT_EXPIRATION=86400000
JWT_REFRESH_EXPIRATION=604800000
```

> Не добавляйте реальные пароли и JWT-секреты в Git.

---

## 🚀 Запуск

### Требования

* JDK 17+
* PostgreSQL
* Maven

Создайте базу данных:

```sql
CREATE DATABASE placeinru_db;
```

Запустите приложение:

```bash
mvn spring-boot:run
```

После запуска:

```text
http://localhost:8080
```

---

## 🧪 Тестирование

```bash
mvn test
```

Критическая бизнес-логика тестируется отдельно, в первую очередь валидация маршрута и расчёт бюджета.

---

## 📖 Swagger / OpenAPI

Swagger UI:

```text
http://localhost:8080/swagger-ui.html
```

OpenAPI:

```text
http://localhost:8080/v3/api-docs
```
