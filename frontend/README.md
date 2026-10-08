# PlaceinRU Frontend

Приложение на React и Vite: публичный landing и личный кабинет для планирования путешествий. Визуальные ориентиры — локальные изображения `src/assets/design-reference/landing-reference.png` и `service-reference.png`. Это референсы для композиции и стиля, а не готовые страницы: интерфейс собран из React-компонентов.

## Запуск

Требуется Node.js 20 или новее.

```bash
npm install
cp .env.example .env
npm run dev
```

Проверьте адреса API в `.env` перед запуском. Frontend не подменяет ответы API демонстрационными данными, если Backend или MRT недоступны.

| Переменная                  | Назначение                              | Локальное значение по умолчанию |
| --------------------------- | --------------------------------------- | ------------------------------- |
| `VITE_BACKEND_URL`          | Путь Java Backend API в браузере        | `/backend`                      |
| `VITE_MRT_URL`              | Путь MRT API в браузере                 | `/mrt`                          |
| `VITE_BACKEND_PROXY_TARGET` | Адрес Java API для dev-прокси Vite      | `http://localhost:8080`         |
| `VITE_MRT_PROXY_TARGET`     | Адрес MRT для dev-прокси Vite           | `http://localhost:8010`         |
| `VITE_ENABLE_DEMO_MODE`     | Явное включение демонстрационных данных | `false`                         |

Порты по умолчанию соответствуют инструкциям `backend-java/README.md` и `mrt-ai/README.md`. Если MRT запущен на другом порту, поменяйте `VITE_MRT_PROXY_TARGET`. В разработке Vite проксирует `/backend/*` и `/mrt/*`, убирая префикс перед передачей запроса. Для production-хостинга нужно настроить аналогичный reverse proxy на эти пути: Vite dev proxy в production не работает.

## Страницы и маршруты

| Маршрут                                      | Экран                                                                             |
| -------------------------------------------- | --------------------------------------------------------------------------------- |
| `/`                                          | Landing: возможности продукта, шаги, направления, CTA и FAQ                       |
| `/login`, `/register`                        | Вход и регистрация через Backend                                                  |
| `/app`                                       | Кабинет: реальные сохранённые поездки и регионы из MRT-каталога                   |
| `/app/misha`                                 | MRT-сессия, форма параметров, рекомендации и сохранение поездки                   |
| `/app/trips`                                 | Список поездок из Backend, фильтры и удаление                                     |
| `/app/trips/:id/overview`                    | Сводка Trip и реальные дни/пункты, если они есть в ответе Backend                 |
| `/app/trips/:id/tickets`                     | Транспортные пункты сохранённого маршрута и состояние отсутствия live-предложений |
| `/app/trips/:id/hotels`                      | Отели, если они есть в маршруте; live-поиск пока не подключён                     |
| `/app/trips/:id/route`                       | Дни и пункты маршрута из Backend                                                  |
| `/app/trips/:id/attractions`, `/restaurants` | Пункты соответствующей категории из сохранённого маршрута                         |
| `/app/trips/:id/budget`                      | Сводка бюджета из Backend                                                         |
| `/app/trips/:id/documents`                   | Состояние ожидания серверного API документов                                      |
| `/app/favorites`                             | Избранные регионы MRT-каталога в локальном хранилище браузера                     |
| `/app/profile`                               | Данные профиля из Backend                                                         |

Все страницы сервиса используют общий responsive shell: sidebar на широком экране и drawer на телефоне. Вкладки Trip — отдельные URL, а не только переключатели вида.

## Архитектура

```text
src/
├── api/
│   ├── client.js       # HTTP, base URL, JWT, refresh, единые ошибки
│   ├── auth.js         # Реальные методы AuthController
│   ├── trips.js        # Реальные методы TripController и маршрутных endpoint
│   └── mrt.js          # MRT sessions, turns, recommendations, catalog
├── auth/
│   └── AuthProvider.jsx # Текущий пользователь и сессия входа
├── router/
│   └── Router.jsx      # SPA history routing и ссылки без внешнего router package
├── layouts/
│   └── AppLayout/      # Sidebar, mobile drawer, общая оболочка кабинета
├── components/
│   └── common/         # Переиспользуемые SVG-иконки и состояния загрузки/ошибок
├── pages/
│   ├── LandingPage/    # Публичная продуктовая страница
│   ├── AuthPage/       # Вход и регистрация
│   ├── DashboardPage/  # Кабинет, поездки и каталог регионов
│   ├── MishaPage/      # Диалог и последовательность создания поездки
│   ├── TripsPage/      # Список Trip
│   ├── TripPage/       # Overview, route, budget и категории Trip
│   ├── FavoritesPage/  # Временное локальное избранное
│   └── ProfilePage/    # Профиль пользователя
├── assets/
│   ├── design-reference/ # Два primary design references
│   ├── figma/            # Локальные иллюстрации, фото и маскот
│   └── data/             # Геоданные карты, используемые существующей картой
├── App.jsx            # Выбор страницы и защита `/app`
├── App.css            # Общие design tokens PlaceinRU
└── main.jsx           # React mount и локальные шрифты Fontsource
```

Существующие компоненты предыдущего публичного макета сохранены в `src/components/` и не включены в новые маршруты, если не переиспользуются. Новая главная использует новые секционные компоненты внутри `pages/LandingPage` и общие `components/common`.

## Потоки данных и API

**Auth → Backend.** `POST /api/v1/auth/register`, `POST /login`, `POST /refresh`, `GET /me`. Фактический `AuthResponse` содержит `accessToken`, `refreshToken`, `email`, `name`; профиль читается из `UserResponse`. Токены сохраняются в `sessionStorage`, Bearer добавляется централизованным клиентом. При 401 выполняется один refresh и повтор исходного запроса. JWT не отправляется MRT.

**Trip → Backend.** Frontend напрямую использует `POST /api/v1/trips`, `GET /api/v1/trips`, `GET/PATCH/DELETE /api/v1/trips/{id}`, `GET /api/v1/trips/{id}/budget`, `POST /api/v1/trips/items`, `POST /api/v1/trips/{id}/items/{itemId}/replace`, `POST /api/v1/trips/{id}/route/rebuild` и `GET /api/v1/trips/{id}/validate`. Сохранённая поездка и бюджет читаются как данные источника истины. JSON-поля соответствуют Java DTO (например `startDate`, `destination`, `adults`, `children`, `budget`).

**Миша → MRT.** Frontend использует `POST /v1/sessions`, `GET /v1/sessions/{id}`, `PATCH /v1/sessions/{id}/trip`, `POST /v1/sessions/{id}/turns`, `POST /v1/sessions/{id}/select-region`, `GET /v1/catalog/regions` и `POST /v1/recommend`. Сессия и `state_version` берутся из ответа MRT. Для каждой операции создаётся request ID; конфликт 409 перечитывает текущую сессию. В MRT не передаётся JWT, поскольку текущие session endpoints его не требуют.

В dev браузер обращается только к origin Vite. Префиксы `/backend` и `/mrt` проксируются в соответствующие API, поэтому фронтенду не требуется CORS от Java/MRT на локальной машине. При развёртывании необходимо повторить это правило на веб-сервере или ingress.

## Ограничения контрактов

Фактические Java controllers и DTO проверены read-only. Текущий Backend/MRT позволяют регистрировать и авторизовать пользователя, читать/сохранять Trip, читать бюджет, работать с днями/пунктами маршрута, вести MRT-сессию и выбирать предложенный регион. Поэтому этот путь подключён к реальным endpoint.

В просмотренных backend controllers нет отдельных API для live-предложений билетов/отелей/ресторанов, бронирований и ссылок покупки, загрузки/скачивания документов, синхронизации избранного, редактирования профиля, удаления/перестановки пунктов маршрута или versioned preview/apply ChangeSet. В текущем MRT нет генерации RouteProposal/готового маршрута и поддержки связки сессии с сохранённым Java Trip. Интерфейс явно сообщает об этих ограничениях, не симулирует успешные действия и не выдумывает цены, наличие или booking URL.

Пункты в категорийных вкладках появляются только из `TripResponse.days[].items[]`. Карта Trip не рисует вымышленную геометрию: Java DTO сейчас не возвращает координаты маршрутных пунктов. Избранные направления можно хранить локально, но UI предупреждает, что они не синхронизированы с Backend. Каталог и поездки не заполняются локальными фиктивными записями.

## Дизайн и доступность

- Дизайн-токены оранжевого shell, кремовых карточек, зелёных действий и радиусов находятся в `src/App.css`.
- Шрифты Manrope, Inter, Balsamiq Sans и другие используются локально через Fontsource в `src/main.jsx`.
- Иллюстрации и маскот берутся только из `src/assets/figma`; во время работы нет внешней загрузки изображений или шрифтов.
- Семантические ссылки/кнопки, подписи полей, keyboard focus, aria-label для иконок управления и `prefers-reduced-motion` предусмотрены в интерфейсе.
- Landing, формы, sidebar/drawer, карточки и вкладки адаптируются под desktop, tablet и mobile.

## Команды

```bash
npm run lint
npm run build
npm run format:check
```

`npm run format` форматирует исходники и документацию Prettier.
