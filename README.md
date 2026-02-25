# Prostoi-CRM: Полное руководство по выполнению проекта

# Prostoi-CRM: Полное руководство по выполнению проекта 

## 1. Структура проекта 

```
prostoi-crm/
├── manage.py
├── .gitignore
├── requirements/
│   ├── base.txt          
│   ├── dev.txt            
│   └── prod.txt           
├── logs/                 
├── apps/               
│   ├── users/            
│      ├── models.py
│      ├── serializers.py
│      ├── views.py
|   ├── ...
├── settings/             
│   ├── .env              
│   ├── conf.py            
│   ├── base.py           
│   ├── urls.py            
│   ├── wsgi.py
│   ├── asgi.py
│   └── env/              
│       ├── local.py      
│       └── prod.py       
├── locale/               
│   ├── ru/
│   └── kk/
├── templates/             
│   └── emails/
│       └── welcome/
├── scripts/               
│   └── start.sh           
├── docs/                  
│   └── erd.png            
└── README.md
```

### 2.1. Переменные окружения

Все переменные имеют префикс `CRM_` (например, `CRM_SECRET_KEY`, `CRM_REDIS_URL`).  
Файл `settings/.env` никогда не коммитится. В репозитории должен быть `settings/.env.example` с заполнителями.

**Порядок загрузки настроек:**  
`manage.py` читает переменную `CRM_ENV_ID` из `.env` и подставляет соответствующий файл из `settings/env/` (например, `local.py` или `prod.py`).  
`local.py` импортирует `base.py`, `base.py` импортирует `conf.py`, который читает `.env`.

## 3. Модели и ERD

Перед написанием кода создайте ER-диаграмму всех моделей. Сохраните её в `docs/erd.png` и вставьте в `README.md`.

### 3.1. Приложение `users` — кастомный пользователь
w
- Модель `User` наследует `AbstractBaseUser` и `PermissionsMixin`.
- Поля:
  - `email` (`EmailField`, `unique`) — поле для логина.
  - `first_name` (`CharField`, max_length=50, required)
  - `last_name` (`CharField`, max_length=50, required)
  - `is_active` (`BooleanField`, default=True)
  - `is_staff` (`BooleanField`, default=False)
  - `date_joined` (`DateTimeField`, auto_now_add=True)
  - `avatar` (`ImageField`, blank=True, null=True)
  - **Для hw2** добавьте:
    - `language` (`CharField`, choices=('en','ru','kk'), default='en')
    - `timezone` (`CharField`, max_length=50, default='UTC')
- Менеджер (`UserManager`) с методами `create_user` и `create_superuser`, нормализует email (нижний регистр) и хеширует пароль.
- В настройках `base.py` обязательно: `AUTH_USER_MODEL = 'users.User'`.

### 3.2. Приложение `crm` — бизнес-модели

#### Category (категория продуктов или сделок)
- `name` (`CharField`, max_length=100, unique)
- `slug` (`SlugField`, unique)
добавьте мультиязычность: вместо одного поля name создайте отдельную модель перевода или используйте библиотеку `django-modeltranslation`. Либо храните JSON с переводами. Упрощённо: можно сделать поля `name_en`, `name_ru`, `name_kk`.

#### Tag (теги для задач или продуктов)
- `name` (`CharField`, max_length=50, unique)
- `slug` (`SlugField`, unique)

#### Client
- `first_name` (`CharField`)
- `last_name` (`CharField`)
- `email` (`EmailField`, unique)
- `phone` (`CharField`, blank=True)
- `address` (`TextField`, blank=True)
- `created_at` (`DateTimeField`, auto_now_add=True)
- `updated_at` (`DateTimeField`, auto_now=True)

#### Product
- `name` (`CharField`, max_length=200)
- `slug` (`SlugField`, unique)
- `category` (`ForeignKey` to `Category`, on_delete=SET_NULL, null=True)
- `tags` (`ManyToManyField` to `Tag`, blank=True)
- `price` (`DecimalField`, max_digits=10, decimal_places=2)
- `description` (`TextField`, blank=True)
- `in_stock` (`BooleanField`, default=True)
- `created_at` (`DateTimeField`, auto_now_add=True)
- `updated_at` (`DateTimeField`, auto_now=True)

#### Deal (сделка)
- `client` (`ForeignKey` to `Client`, on_delete=CASCADE)
- `product` (`ForeignKey` to `Product`, on_delete=SET_NULL, null=True, blank=True)
- `title` (`CharField`, max_length=200)
- `amount` (`DecimalField`, max_digits=10, decimal_places=2)
- `status` (`CharField`, choices=['new','in_progress','closed_won','closed_lost'], default='new')
- `created_at` (`DateTimeField`, auto_now_add=True)
- `updated_at` (`DateTimeField`, auto_now=True)
- `closed_at` (`DateTimeField`, null=True, blank=True)

#### Task (задача)
- `title` (`CharField`, max_length=200)
- `description` (`TextField`, blank=True)
- `assigned_to` (`ForeignKey` to `User`, on_delete=CASCADE, related_name='tasks')
- `client` (`ForeignKey` to `Client`, on_delete=CASCADE, null=True, blank=True)
- `deal` (`ForeignKey` to `Deal`, on_delete=CASCADE, null=True, blank=True)
- `status` (`CharField`, choices=['pending','in_progress','completed'], default='pending')
- `due_date` (`DateTimeField`, null=True, blank=True)
- `created_at` (`DateTimeField`, auto_now_add=True)
- `updated_at` (`DateTimeField`, auto_now=True)

#### Comment (комментарий к задаче или сделке)
- `author` (`ForeignKey` to `User`, on_delete=CASCADE)
- `content_type` (`ForeignKey` to `ContentType`) — если использовать generic relations, либо привязать напрямую к Task/Deal. Для простоты сделайте две модели: `TaskComment` и `DealComment`. Но лучше через GenericForeignKey.
- `object_id` (`PositiveIntegerField`)
- `content_object` (GenericForeignKey)
- `body` (`TextField`)
- `created_at` (`DateTimeField`, auto_now_add=True)

## 4. Аутентификация и JWT 

- Используйте `djangorestframework-simplejwt`.
- Настройте `DEFAULT_AUTHENTICATION_CLASSES` в `REST_FRAMEWORK` на `JWTAuthentication`.
- Эндпоинты:
  - `POST /api/auth/register/` — без аутентификации. Принимает email, first_name, last_name, password, password2. Возвращает данные пользователя и пару токенов.
  - `POST /api/auth/token/` — получение токенов (логин) — встроенное представление `TokenObtainPairView`.
  - `POST /api/auth/token/refresh/` — обновление access-токена — встроенное `TokenRefreshView`.
-  добавьте эндпоинты:
  - `PATCH /api/auth/language/` — изменение языка пользователя (принимает `language`, валидация по списку).
  - `PATCH /api/auth/timezone/` — изменение временной зоны (валидация по IANA).

## 5. Эндпоинты CRM 

Используйте `ViewSet` и `DefaultRouter`. Для моделей, использующих slug, укажите `lookup_field = 'slug'`.

Минимальный набор :

- `GET /api/clients/` — список клиентов (пагинация, фильтрация)
- `POST /api/clients/` — создание клиента (только аутентифицированные)
- `GET /api/clients/{id}/` — детали клиента
- `PATCH /api/clients/{id}/` — обновление (только авторы? или менеджеры)
- `DELETE /api/clients/{id}/` — удаление
- `GET /api/products/` — список продуктов (с фильтрацией по категории, цене)
- `POST /api/products/` — создание продукта
- `GET /api/products/{slug}/` — детали продукта
- `PATCH /api/products/{slug}/` — обновление
- `DELETE /api/products/{slug}/` — удаление
- `GET /api/deals/` — список сделок
- `POST /api/deals/` — создание сделки
- `GET /api/deals/{id}/` — детали сделки
- `PATCH /api/deals/{id}/` — обновление
- `DELETE /api/deals/{id}/` — удаление
- `GET /api/tasks/` — список задач
- `POST /api/tasks/` — создание задачи
- `GET /api/tasks/{id}/` — детали задачи
- `PATCH /api/tasks/{id}/` — обновление
- `DELETE /api/tasks/{id}/` — удаление
- `GET /api/tasks/{id}/comments/` — список комментариев к задаче
- `POST /api/tasks/{id}/comments/` — добавление комментария

Для вложенных комментариев можно использовать `@action` на TaskViewSet или drf-nested-routers.

**Фильтрация **  
Обязательно реализуйте фильтрацию для хотя бы одного эндпоинта (например, `?status=open` для сделок, `?category=slug` для продуктов). Используйте `django-filter`.

**Permissions **  
- Для чтения (`list`, `retrieve`) — доступно всем (включая анонимов), но только для объектов со статусом `published` (если есть такая концепция). Для CRM, вероятно, все данные должны быть доступны только аутентифицированным. Уточните требование. По аналогии с блогом: неопубликованные посты видны только автору. У нас может быть статус сделки, но скрывать их не нужно. Проще сделать так:
  - Любой аутентифицированный пользователь может читать всё.
  - Создание, обновление, удаление — только аутентифицированные.
  - Редактирование/удаление объекта — только его создатель (или менеджер). Реализуйте кастомное permission `IsOwnerOrReadOnly` для задач и сделок (поле `assigned_to` или `created_by`). Добавьте в модели поле `created_by` (ForeignKey to User, auto-set).

 добавьте языковую адаптацию:
- Названия категорий должны возвращаться на языке пользователя. Если используется отдельная модель перевода, то сериализатор должен подбирать нужное поле.
- Даты (created_at, updated_at) в ответах должны быть отформатированы с учётом локали и часового пояса пользователя. Для анонимов — UTC.
- Все сообщения об ошибках (в том числе стандартные DRF) должны переводиться на активный язык. Используйте стандартные механизмы перевода Django (`gettext`, `ugettext_lazy` в коде, `make messages`).

## 6. Логирование 

Настройте словарь `LOGGING` в `base.py`:

- Форматтеры:
  - `simple` — уровень и сообщение.
  - `verbose` — время, уровень, логгер, модуль, сообщение.
- Обработчики:
  - `console` — `StreamHandler`, уровень `DEBUG`, форматтер `simple`.
  - `file` — `RotatingFileHandler` (`logs/app.log`), уровень `WARNING`, макс. размер 5 МБ, 3 бэкапа, форматтер `verbose`.
  - `debug_file` — `FileHandler` (`logs/debug_requests.log`), уровень `DEBUG`, форматтер `verbose`, активен только при `DEBUG=True` (используйте фильтр `require_debug_true`).
- Логгеры:
  - `'users'` и `'crm'` — уровень `DEBUG`, все обработчики, `propagate=False`.
  - `'django.request'` — уровень `WARNING`, обработчик `file`, `propagate=False`.

В коде обязательно используйте логирование:
- При регистрации: `logger.info('Registration attempt: %s', email)`, при успехе/неудаче.
- При логине: аналогично.
- При создании/изменении/удалении объектов CRM.
- В исключениях: `logger.exception(...)`.

## 7. Redis 

Установите Redis локально или через Docker. Добавьте в `base.txt` зависимости `django-redis` и `redis`.

### 7.1. Кэширование 

- Настройте кэш-бэкенд на Redis.
- Занесите в кэш список опубликованных (или всех) сделок/задач на 60 секунд. Например, кэшируйте ответ `GET /api/deals/`. Инвалидируйте кэш при создании, обновлении или удалении сделки. Можно использовать `cache_page` декоратор или ручное кэширование. Объясните выбор в комментарии.

### 7.2. Rate limiting 

Реализуйте ограничение частоты запросов с помощью Redis. Подойдёт библиотека `django-ratelimit` или самописный декоратор с использованием Redis.

- `POST /api/auth/register/` — не более 5 запросов в минуту с одного IP.
- `POST /api/auth/token/` — не более 10 запросов в минуту с одного IP.
- `POST /api/deals/` (создание сделки) — не более 20 запросов в минуту на пользователя.

При превышении лимита возвращайте `429 Too Many Requests` с телом `{"detail": "Too many requests. Try again later."}`.

### 7.3. Pub/Sub 

При создании нового комментария (например, к задаче) публикуйте JSON-событие в Redis-канал `comments`. Событие должно содержать как минимум:
```json
{
  "task_id": 1,
  "author_id": 5,
  "body": "Текст комментария",
  "created_at": "2026-02-25T12:00:00Z"
}
```
Напишите management command `python manage.py listen_comments`, которая подписывается на канал и выводит полученные сообщения в консоль. Используйте синхронный клиент Redis.

### 7.4. Асинхронный Redis listener 

Перепишите команду `listen_comments` с использованием асинхронного клиента Redis (`aioredis` или `redis.asyncio`). Команда должна работать в асинхронном цикле событий.

## 8. Мультиязычность и локализация 

- Включите поддержку языков `en`, `ru`, `kk` в `LANGUAGES` и `LOCALE_PATHS`.
- Создайте middleware, который определяет язык запроса в порядке:
  1. Язык из профиля аутентифицированного пользователя (поле `language`).
  2. Параметр запроса `?lang=...`.
  3. Заголовок `Accept-Language`.
  4. Значение по умолчанию (`en`).
- Установите часовой пояс для запроса (для аутентифицированных пользователей — из поля `timezone`, для анонимов — UTC).
- Все строки, возвращаемые в API (включая сообщения валидации), должны быть переведены. Используйте `gettext` (`_`) в коде и создайте файлы перевода.
- **Перевод названий категорий:** либо используйте отдельные поля (`name_en`, `name_ru`, `name_kk`), либо модель `CategoryTranslation`. В сериализаторе возвращайте нужное поле в зависимости от активного языка.
- **Приветственное письмо при регистрации** отправляется на языке, выбранном пользователем при регистрации (поле `language` в запросе). Используйте шаблоны писем в `templates/emails/welcome/` с интернационализацией. В разработке письма выводятся в консоль (настройте `EMAIL_BACKEND` как `console`).
- **Кэширование с учётом языка:** ключ кэша для списка сделок должен включать код языка. Например, `deals_list_en`, `deals_list_ru`. Инвалидируйте кэш для всех языков при изменении данных.

## 9. Документация API 

- Установите `drf-spectacular`.
- Настройте генерацию схемы, подключите вьюхи.
- Эндпоинты документации:
  - `/api/docs/` — Swagger UI
  - `/api/redoc/` — ReDoc
  - `/api/schema/` — OpenAPI схема
- Для каждого эндпоинта укажите:
  - Краткое описание (summary)
  - Подробное описание (description): что делает, нужна ли аутентификация, какие сайд-эффекты, особенности языка/таймзоны.
  - Тело запроса (для POST/PATCH)
  - Возможные коды ответов с примерами: 200, 201, 400, 401, 403, 404, 429.
  - Тэг для группировки.
  - Пример запроса и ответа (можно через `examples` или `extend_schema`).

## 10. Shell-скрипт `scripts/start.sh` 

Скрипт должен выполнять полное развёртывание проекта одной командой (предполагается SQLite для локальной разработки). Обязательные шаги:

1. Проверить наличие и заполненность всех переменных окружения, необходимых проекту (читать `.env`). Если переменной нет — вывести её имя и завершиться с ошибкой.
2. Создать виртуальное окружение (если отсутствует) и установить зависимости из `requirements/dev.txt`.
3. Применить миграции: `python manage.py migrate`.
4. Собрать статику: `python manage.py collectstatic --noinput`.
5. Скомпилировать переводы: `python manage.py compilemessages`.
6. Создать суперпользователя (с захардкоженными логином/паролем, например `admin` / `admin123`). Если уже существует — пропустить.
7. Наполнить БД тестовыми данными (через management command `fill_db` или прямо в скрипте). Данные должны быть достаточными для проверки пагинации, фильтрации, языков.
8. Запустить dev-сервер.

Если скрипт запускается повторно, он не должен падать (проверять существование суперпользователя, виртуального окружения и т.д.). При ошибке любого шага скрипт завершается и печатает, какой шаг провалился.

После запуска сервера скрипт выводит резюме:
```
API: http://127.0.0.1:8000/api/
Swagger UI: http://127.0.0.1:8000/api/docs/
ReDoc: http://127.0.0.1:8000/api/redoc/
Admin: http://127.0.0.1:8000/admin/
Superuser: admin / admin123
```

## 11. Асинхронный эндпоинт статистики 

Добавьте эндпоинт `GET /api/stats/` без аутентификации, который возвращает:

```json
{
  "crm": {
    "total_clients": 42,
    "total_deals": 137,
    "total_tasks": 89
  },
  "exchange_rates": {
    "KZT": 450.23,
    "RUB": 89.10,
    "EUR": 0.92
  },
  "current_time": "2026-02-25T15:30:00+06:00"
}
```

- Количество клиентов, сделок и задач берётся из базы данных.
- Курсы валют запрашиваются асинхронно с `https://open.er-api.com/v6/latest/USD` (извлечь только KZT, RUB, EUR).
- Текущее время для Алматы запрашивается асинхронно с `https://timeapi.io/api/time/current/zone?timeZone=Asia/Almaty` (поле `dateTime`).
- Два внешних запроса должны выполняться **конкурентно** с помощью `asyncio.gather`. Общее время ответа не должно превышать максимальное из двух.
- Используйте `httpx.AsyncClient`.

В коде представления и команды оставьте комментарий, почему выбран асинхронный подход и что было бы при синхронной реализации.

## 12. Чеклист 
- [ ] Кастомная модель User с email как логин.
- [ ] JWT (регистрация, токен, рефреш).
- [ ] Модели Client, Product, Deal, Task, Category, Tag, Comment (или аналоги).
- [ ] CRUD для всех моделей (минимум 10 эндпоинтов).
- [ ] Фильтрация на одном из эндпоинтов.
- [ ] Кастомные permission (например, `IsOwnerOrReadOnly` для задач).
- [ ] Логирование с разделением на файлы и консоль.
- [ ] Redis: кэширование списка сделок (с инвалидацией).
- [ ] Redis: rate limiting на регистрацию, логин, создание сделок.
- [ ] Redis pub/sub + команда `listen_comments`.
- [ ] ER-диаграмма в `docs/` и README.
- [ ] Разделение настроек и требований.
- [ ] Все переменные с префиксом `CRM_`.

- [ ] Поля языка и часового пояса у User, эндпоинты для их обновления.
- [ ] Middleware определения языка и часового пояса.
- [ ] Перевод всех пользовательских строк (не менее 10 на ru и kk).
- [ ] Названия категорий мультиязычны.
- [ ] Даты в ответах конвертируются в локальный пояс и формат.
- [ ] Приветственное письмо на выбранном языке (вывод в консоль).
- [ ] Кэш списка сделок учитывает язык.
- [ ] Полная документация через drf-spectacular (все эндпоинты, коды, примеры).
- [ ] Скрипт `start.sh` полностью автоматизирует развёртывание.
- [ ] Асинхронный эндпоинт `/api/stats/` с конкурентными запросами.
- [ ] Асинхронная команда `listen_comments`.
- [ ] Комментарии в async-коде с объяснением выбора.
- [ ] Файл `.env.example` в репозитории.

