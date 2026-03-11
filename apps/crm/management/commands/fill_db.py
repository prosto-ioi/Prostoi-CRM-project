"""
Management command для наполнения БД тестовыми данными.
Запуск: python manage.py fill_db
Повторный запуск безопасен — дубликаты не создаются.
"""
import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.contrib.contenttypes.models import ContentType

from crm.models import Category, Tag, Client, Product, Deal, Task, Comment


class Command(BaseCommand):
    help = 'Наполняет БД тестовыми данными'

    def handle(self, *args, **options):
        self.stdout.write('in progress... \n')
        self.User = get_user_model()

        self._create_users()
        self._create_categories()
        self._create_tags()
        self._create_clients()
        self._create_products()
        self._create_deals()
        self._create_tasks()
        self._create_comments()

        self.stdout.write(self.style.SUCCESS('\ndone'))
        self._print_summary()

    def _create_users(self):
        users_data = [
            {'email': 'manager1@crm.com', 'first_name': 'Алихан', 'last_name': 'Сейткали', 'language': 'ru', 'timezone': 'Asia/Almaty'},
            {'email': 'manager2@crm.com', 'first_name': 'Айгерим', 'last_name': 'Жумабаева', 'language': 'kk', 'timezone': 'Asia/Almaty'},
            {'email': 'manager3@crm.com', 'first_name': 'Ivan', 'last_name': 'Petrov', 'language': 'en', 'timezone': 'UTC'},
            {'email': 'staff@crm.com', 'first_name': 'Admin', 'last_name': 'Staff', 'language': 'ru', 'timezone': 'Asia/Almaty'},
        ]
        for data in users_data:
            user, created = self.User.objects.get_or_create(
                email=data['email'],
                defaults={**data, 'is_active': True}
            )
            if created:
                user.set_password('Test1234!')
                if data['email'] == 'staff@crm.com':
                    user.is_staff = True
                user.save()
        self.stdout.write(f'Пользователи: {self.User.objects.count()} шт.')

    def _create_categories(self):
        categories = [
            {'name_en': 'Software', 'name_ru': 'Программное обеспечение', 'name_kk': 'Бағдарламалық жасақтама', 'slug': 'software'},
            {'name_en': 'Hardware', 'name_ru': 'Оборудование', 'name_kk': 'Жабдық', 'slug': 'hardware'},
            {'name_en': 'Services', 'name_ru': 'Услуги', 'name_kk': 'Қызметтер', 'slug': 'services'},
            {'name_en': 'Consulting', 'name_ru': 'Консалтинг', 'name_kk': 'Консалтинг', 'slug': 'consulting'},
            {'name_en': 'Support', 'name_ru': 'Поддержка', 'name_kk': 'Қолдау', 'slug': 'support'},
        ]
        for data in categories:
            Category.objects.get_or_create(slug=data['slug'], defaults=data)
        self.stdout.write(f'Категории: {Category.objects.count()} шт.')

    def _create_tags(self):
        tags = [
            {'name': 'urgent', 'slug': 'urgent'},
            {'name': 'vip', 'slug': 'vip'},
            {'name': 'new-client', 'slug': 'new-client'},
            {'name': 'enterprise', 'slug': 'enterprise'},
            {'name': 'discount', 'slug': 'discount'},
            {'name': 'renewal', 'slug': 'renewal'},
        ]
        for data in tags:
            Tag.objects.get_or_create(slug=data['slug'], defaults=data)
        self.stdout.write(f'Теги: {Tag.objects.count()} шт.')

    def _create_clients(self):
        clients_data = [
            {'first_name': 'Нурлан', 'last_name': 'Абенов', 'email': 'nurlan@kaspi.kz', 'phone': '+77011234567', 'address': 'Алматы, ул. Абая 1'},
            {'first_name': 'Динара', 'last_name': 'Сагинтаева', 'email': 'dinara@halyk.kz', 'phone': '+77022345678', 'address': 'Астана, пр. Республики 10'},
            {'first_name': 'Максим', 'last_name': 'Иванов', 'email': 'maxim@kcell.kz', 'phone': '+77033456789', 'address': 'Алматы, ул. Достык 5'},
            {'first_name': 'Айша', 'last_name': 'Бекова', 'email': 'aisha@beeline.kz', 'phone': '+77044567890', 'address': 'Шымкент, ул. Байтурсынова 3'},
            {'first_name': 'Сергей', 'last_name': 'Козлов', 'email': 'sergey@aktobe.kz', 'phone': '+77055678901', 'address': 'Актобе, ул. Маресьева 7'},
            {'first_name': 'Зарина', 'last_name': 'Нурмагамбетова', 'email': 'zarina@samruk.kz', 'phone': '+77066789012', 'address': 'Астана, ул. Кабанбай батыра 2'},
            {'first_name': 'Арман', 'last_name': 'Джаксыбеков', 'email': 'arman@kegoc.kz', 'phone': '+77077890123', 'address': 'Алматы, пр. Аль-Фараби 15'},
            {'first_name': 'Ольга', 'last_name': 'Смирнова', 'email': 'olga@kazpost.kz', 'phone': '+77088901234', 'address': 'Алматы, ул. Сейфуллина 20'},
        ]
        for data in clients_data:
            Client.objects.get_or_create(email=data['email'], defaults=data)
        self.stdout.write(f'Клиенты: {Client.objects.count()} шт.')

    def _create_products(self):
        admin = self.User.objects.filter(is_staff=True).first()

        software = Category.objects.get(slug='software')
        hardware = Category.objects.get(slug='hardware')
        services = Category.objects.get(slug='services')
        consulting = Category.objects.get(slug='consulting')
        support = Category.objects.get(slug='support')

        tag_vip = Tag.objects.get(slug='vip')
        tag_enterprise = Tag.objects.get(slug='enterprise')
        tag_discount = Tag.objects.get(slug='discount')

        products_data = [
            {'name': 'CRM Pro License', 'slug': 'crm-pro-license', 'category': software, 'price': '99000.00', 'description': 'Годовая лицензия CRM Pro', 'tags': [tag_vip]},
            {'name': 'CRM Enterprise', 'slug': 'crm-enterprise', 'category': software, 'price': '450000.00', 'description': 'Корпоративная лицензия CRM', 'tags': [tag_enterprise, tag_vip]},
            {'name': 'Server Setup', 'slug': 'server-setup', 'category': hardware, 'price': '250000.00', 'description': 'Настройка и установка сервера', 'tags': [tag_enterprise]},
            {'name': 'Cloud Backup', 'slug': 'cloud-backup', 'category': services, 'price': '15000.00', 'description': 'Облачное резервное копирование', 'tags': [tag_discount]},
            {'name': 'IT Consulting', 'slug': 'it-consulting', 'category': consulting, 'price': '80000.00', 'description': 'Консультации по IT-инфраструктуре', 'tags': []},
            {'name': 'Support Plan Basic', 'slug': 'support-plan-basic', 'category': support, 'price': '25000.00', 'description': 'Базовый план поддержки', 'tags': [tag_discount]},
            {'name': 'Support Plan Premium', 'slug': 'support-plan-premium', 'category': support, 'price': '75000.00', 'description': 'Премиум план поддержки 24/7', 'tags': [tag_vip, tag_enterprise]},
            {'name': 'Mobile CRM App', 'slug': 'mobile-crm-app', 'category': software, 'price': '35000.00', 'description': 'Мобильное приложение CRM', 'tags': []},
        ]
        for data in products_data:
            tags = data.pop('tags')
            product, created = Product.objects.get_or_create(
                slug=data['slug'],
                defaults={**data, 'created_by': admin}
            )
            if created and tags:
                product.tags.set(tags)
        self.stdout.write(f'Продукты: {Product.objects.count()} шт.')

    def _create_deals(self):
        clients = list(Client.objects.all())
        products = list(Product.objects.all())
        managers = list(self.User.objects.filter(is_staff=False))

        statuses = ['new', 'in_progress', 'closed_won', 'closed_lost']
        titles = [
            'Внедрение CRM системы', 'Обновление лицензии',
            'Подключение облачного бэкапа', 'Консультация по IT',
            'Покупка оборудования', 'Продление поддержки',
            'Новый корпоративный контракт', 'Пилотный проект',
            'Расширение лицензии', 'Техническое обслуживание',
        ]
        for i, title in enumerate(titles):
            client = clients[i % len(clients)]
            product = products[i % len(products)]
            manager = managers[i % len(managers)] if managers else None
            deal_status = statuses[i % len(statuses)]
            amount = float(product.price) * random.randint(1, 5)
            closed_at = timezone.now() - timedelta(days=random.randint(1, 30)) if deal_status in ['closed_won', 'closed_lost'] else None

            Deal.objects.get_or_create(
                title=title,
                client=client,
                defaults={
                    'product': product,
                    'amount': amount,
                    'status': deal_status,
                    'closed_at': closed_at,
                    'created_by': manager,
                }
            )
        self.stdout.write(f'Сделки: {Deal.objects.count()} шт.')

    def _create_tasks(self):
        users = list(self.User.objects.all())
        deals = list(Deal.objects.all())
        clients = list(Client.objects.all())

        tasks_data = [
            {'title': 'Позвонить клиенту для уточнения требований', 'status': 'pending'},
            {'title': 'Подготовить коммерческое предложение', 'status': 'in_progress'},
            {'title': 'Провести демонстрацию продукта', 'status': 'pending'},
            {'title': 'Согласовать договор с юристами', 'status': 'in_progress'},
            {'title': 'Отправить счёт на оплату', 'status': 'completed'},
            {'title': 'Установить и настроить CRM', 'status': 'pending'},
            {'title': 'Обучение сотрудников клиента', 'status': 'pending'},
            {'title': 'Проверить статус оплаты', 'status': 'in_progress'},
            {'title': 'Написать технический отчёт', 'status': 'completed'},
            {'title': 'Запланировать follow-up встречу', 'status': 'pending'},
            {'title': 'Обновить данные клиента в системе', 'status': 'completed'},
            {'title': 'Провести аудит IT-инфраструктуры', 'status': 'in_progress'},
        ]
        for i, data in enumerate(tasks_data):
            assigned = users[i % len(users)]
            deal = deals[i % len(deals)]
            client = clients[i % len(clients)]
            due_date = timezone.now() + timedelta(days=random.randint(1, 30))

            Task.objects.get_or_create(
                title=data['title'],
                defaults={
                    'description': f'Описание: {data["title"]}',
                    'assigned_to': assigned,
                    'client': client,
                    'deal': deal,
                    'status': data['status'],
                    'due_date': due_date,
                }
            )
        self.stdout.write(f'Задачи: {Task.objects.count()} шт.')

    def _create_comments(self):
        users = list(self.User.objects.all())
        tasks = list(Task.objects.all()[:5])
        deals = list(Deal.objects.all()[:5])

        ct_task = ContentType.objects.get_for_model(Task)
        ct_deal = ContentType.objects.get_for_model(Deal)

        task_comments = [
            'Связался с клиентом, ждём ответа',
            'Документы отправлены на проверку',
            'Задача выполнена успешно',
            'Нужно уточнить детали у менеджера',
            'Перенесено на следующую неделю',
        ]
        deal_comments = [
            'Клиент заинтересован, продолжаем переговоры',
            'Отправили КП, ждём обратной связи',
            'Сделка на финальной стадии согласования',
            'Клиент запросил скидку 10%',
            'Договор подписан, ждём оплаты',
        ]
        for i, task in enumerate(tasks):
            Comment.objects.get_or_create(
                content_type=ct_task,
                object_id=task.id,
                author=users[i % len(users)],
                defaults={'body': task_comments[i]}
            )
        for i, deal in enumerate(deals):
            Comment.objects.get_or_create(
                content_type=ct_deal,
                object_id=deal.id,
                author=users[i % len(users)],
                defaults={'body': deal_comments[i]}
            )
        self.stdout.write(f'  💬 Комментарии: {Comment.objects.count()} шт.')

    def _print_summary(self):
        self.stdout.write('\n📊 Итого в БД:')
        self.stdout.write(f'   Пользователи: {self.User.objects.count()}')
        self.stdout.write(f'   Категории:    {Category.objects.count()}')
        self.stdout.write(f'   Теги:         {Tag.objects.count()}')
        self.stdout.write(f'   Клиенты:      {Client.objects.count()}')
        self.stdout.write(f'   Продукты:     {Product.objects.count()}')
        self.stdout.write(f'   Сделки:       {Deal.objects.count()}')
        self.stdout.write(f'   Задачи:       {Task.objects.count()}')
        self.stdout.write(f'   Комментарии:  {Comment.objects.count()}')
        self.stdout.write('\n🔑 Тестовые аккаунты (пароль: Test1234!):')
        self.stdout.write('   manager1@crm.com — менеджер (язык: ru)')
        self.stdout.write('   manager2@crm.com — менеджер (язык: kk)')
        self.stdout.write('   manager3@crm.com — менеджер (язык: en)')
        self.stdout.write('   staff@crm.com    — staff/admin')