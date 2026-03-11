# Prostoi CRM

CRM система для управления клиентами, сделками и задачами.

## ER Diagram

![ERD](docs/erd.png)

## Запуск проекта

```bash
# 1. Установить зависимости
pip install -r requirements/dev.txt

# 2. Применить миграции
python manage.py migrate

# 3. Наполнить БД тестовыми данными
python manage.py fill_db

# 4. Запустить сервер
python manage.py runserver
```

## Тестовые аккаунты

| Email | Пароль | Роль |
|-------|--------|------|
| manager1@crm.com | Test1234! | Менеджер (ru) |
| manager2@crm.com | Test1234! | Менеджер (kk) |
| manager3@crm.com | Test1234! | Менеджер (en) |
| staff@crm.com | Test1234! | Staff / Admin |

## API Documentation

| Ссылка | Описание |
|--------|----------|
| http://127.0.0.1:8000/api/docs/ | Swagger UI |
| http://127.0.0.1:8000/api/redoc/ | ReDoc |
| http://127.0.0.1:8000/api/schema/ | OpenAPI схема |
| http://127.0.0.1:8000/admin/ | Django Admin |

## Структура проекта

```
prostoi-crm/
├── manage.py
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── apps/
│   ├── users/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── ...
│   └── crm/
│       ├── models.py
│       ├── serializers.py
│       ├── views.py
│       ├── filters.py
│       ├── permission.py
│       ├── urls.py
│       ├── admin.py
│       └── management/
│           └── commands/
│               └── fill_db.py
├── settings/
│   ├── base.py
│   ├── conf.py
│   ├── urls.py
│   └── env/
│       ├── local.py
│       └── prod.py
├── docs/
│   └── erd.png
└── README.md
```