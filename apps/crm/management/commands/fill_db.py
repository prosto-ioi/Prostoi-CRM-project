"""Management command that seeds the database with realistic test data.

Idempotent — safe to run multiple times; ``get_or_create`` is used everywhere
so duplicates are not created. Demo accounts share a single fixed password
(see :data:`DEMO_PASSWORD`).

Usage::

    python manage.py fill_db
"""
from __future__ import annotations

import random
from datetime import timedelta
from typing import Any, Final

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.utils import timezone

from crm.models import Category, Client, Comment, Deal, Product, Tag, Task

# ─── Constants (no magic numbers / strings buried in functions) ────────────
DEMO_PASSWORD: Final[str] = "Test1234!"  # password for every demo account
STAFF_EMAIL: Final[str] = "staff@crm.com"

# Bounded random ranges — explicit names beat literals scattered in code.
DEAL_AMOUNT_MULTIPLIER_RANGE: Final[tuple[int, int]] = (1, 5)
DEAL_CLOSED_DAYS_AGO_RANGE: Final[tuple[int, int]] = (1, 30)
TASK_DUE_DAYS_AHEAD_RANGE: Final[tuple[int, int]] = (1, 30)

# Only the first N rows get comments to keep the seed dataset small.
COMMENTED_OBJECTS_LIMIT: Final[int] = 5


class Command(BaseCommand):
    """Populate the database with demo users, categories, products, deals, etc."""

    help = "Populate the database with realistic demo data (idempotent)."

    # Will be filled in :meth:`handle` — kept as an instance attribute so the
    # private helpers don't have to receive it as an argument every time.
    User: type[AbstractBaseUser]

    def handle(self, *args: Any, **options: Any) -> None:
        """Entry point — run the seed steps in dependency order."""
        self.stdout.write("Filling database...\n")
        self.User = get_user_model()

        self._create_users()
        self._create_categories()
        self._create_tags()
        self._create_clients()
        self._create_products()
        self._create_deals()
        self._create_tasks()
        self._create_comments()

        self.stdout.write(self.style.SUCCESS("\nDone."))
        self._print_summary()

    #  Users 
    def _create_users(self) -> None:
        """Create three managers (different languages) and one staff admin."""
        users_data: list[dict[str, str]] = [
            {
                "email": "manager1@crm.com", 
                "first_name": "Alikhan",
                "last_name": "Seitkali", 
                "language": "ru", 
                "timezone": "Asia/Almaty",
            },
            {
                "email": "manager2@crm.com",
                  "first_name": "Aigerim",
                "last_name": "Zhumabaeva", 
                "language": "kk", 
                "timezone": "Asia/Almaty",
            },
            {
                "email": "manager3@crm.com", 
                "first_name": "Ivan",
                "last_name": "Petrov", 
                "language": "en", 
                "timezone": "UTC",
            },
            {
                "email": STAFF_EMAIL,
                "first_name": "Admin",
                "last_name": "Staff", 
                "language": "ru", 
                "timezone": "Asia/Almaty",
            },
        ]
        for data in users_data:
            user, created = self.User.objects.get_or_create(  
                email=data["email"],
                defaults={**data, "is_active": True},
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save() 
        self.stdout.write(f"  Users:      {self.User.objects.count()}")

    #  Categories 
    def _create_categories(self) -> None:
        """Seed 5 product categories with EN/RU/KK names."""
        categories: list[dict[str, str]] = [
            {"name_en": "Software", 
             "name_ru": "Программное обеспечение",
             "name_kk": "Бағдарламалық жасақтама", 
             "slug": "software"
             },
            {"name_en": "Hardware", 
             "name_ru": "Оборудование",
             "name_kk": "Жабдық", 
             "slug": "hardware"
             },
            {"name_en": "Services", 
             "name_ru": "Услуги",
             "name_kk": "Қызметтер", 
             "slug": "services"
             },
            {"name_en": "Consulting", 
             "name_ru": "Консалтинг",
             "name_kk": "Консалтинг", 
             "slug": "consulting"
             },
            {"name_en": "Support", 
             "name_ru": "Поддержка",
             "name_kk": "Қолдау", 
             "slug": "support"
             },
        ]
        for data in categories:
            Category.objects.get_or_create(slug=data["slug"], defaults=data)
        self.stdout.write(f"  Categories: {Category.objects.count()}")

    #  Tags 
    def _create_tags(self) -> None:
        """Seed a small fixed tag vocabulary."""
        tags: list[dict[str, str]] = [
            {"name": "urgent", "slug": "urgent"},
            {"name": "vip", "slug": "vip"},
            {"name": "new-client", "slug": "new-client"},
            {"name": "enterprise", "slug": "enterprise"},
            {"name": "discount", "slug": "discount"},
            {"name": "renewal", "slug": "renewal"},
        ]
        for data in tags:
            Tag.objects.get_or_create(slug=data["slug"], defaults=data)
        self.stdout.write(f"  Tags:       {Tag.objects.count()}")

    #  Clients 
    def _create_clients(self) -> None:
        """Seed a handful of clients with realistic-looking KZ data."""
        clients_data: list[dict[str, str]] = [
            {
                "first_name": "Nurlan", "last_name": "Abenov",
                "email": "nurlan@kaspi.kz", "phone": "+77011111111",
                "address": "Almaty, Abay Ave 1",
            },
            {
                "first_name": "Dinara", "last_name": "Sagintayeva",
                "email": "dinara@halyk.kz", "phone": "+77022222222",
                "address": "Astana, Respublika Ave 10",
            },
            {
                "first_name": "Maxim", "last_name": "Ivanov",
                "email": "maxim@kcell.kz", "phone": "+77033333333",
                "address": "Almaty, Dostyk St 5",
            },
            {
                "first_name": "Aisha", "last_name": "Bekova",
                "email": "aisha@beeline.kz", "phone": "+77044444444",
                "address": "Shymkent, Baitursynov St 3",
            },
            {
                "first_name": "Sergey", "last_name": "Kozlov",
                "email": "sergey@aktobe.kz", "phone": "+77055555555",
                "address": "Aktobe, Maresyev St 7",
            },
            {
                "first_name": "Zarina", "last_name": "Nurmagambetova",
                "email": "zarina@samruk.kz", "phone": "+77066666666",
                "address": "Astana, Kabanbay Batyr St 2",
            },
            {
                "first_name": "Arman", "last_name": "Dzhaksybekov",
                "email": "arman@kegoc.kz", "phone": "+77077777777",
                "address": "Almaty, Al-Farabi Ave 15",
            },
            {
                "first_name": "Olga", "last_name": "Smirnova",
                "email": "olga@kazpost.kz", "phone": "+77088888888",
                "address": "Almaty, Seifullin St 20",
            },
            {
                "first_name": "Dauren", "last_name": "Seitkali",
                "email": "dauren@air.kz", "phone": "+77099999999",
                "address": "Almaty, Furmanov St 240",
            },
            {
                "first_name": "Madina", "last_name": "Akhmetova",
                "email": "madina@kztelecom.kz", "phone": "+77010101010",
                "address": "Astana, Beibitshilik St 18",
            },
        ]
        for data in clients_data:
            Client.objects.get_or_create(email=data["email"], defaults=data)
        self.stdout.write(f"  Clients:    {Client.objects.count()}")

    # Products 
    def _create_products(self) -> None:
        """Seed products linked to categories and tags."""
        admin = self.User.objects.filter(is_staff=True).first()  # type: ignore[attr-defined]

        software = Category.objects.get(slug="software")
        hardware = Category.objects.get(slug="hardware")
        services = Category.objects.get(slug="services")
        consulting = Category.objects.get(slug="consulting")
        support = Category.objects.get(slug="support")

        tag_vip = Tag.objects.get(slug="vip")
        tag_enterprise = Tag.objects.get(slug="enterprise")
        tag_discount = Tag.objects.get(slug="discount")

        products_data: list[dict[str, Any]] = [
            {
            "name": "CRM Pro License", 
            "slug": "crm-pro-license",
            "category": software, 
            "price": "99000.00",
            "description": "Annual CRM Pro license", 
            "tags": [tag_vip]
            },
            {
            "name": "CRM Enterprise", 
             "slug": "crm-enterprise",
             "category": software, 
             "price": "450000.00",
             "description": "Enterprise CRM license", 
             "tags": [tag_enterprise, tag_vip]
            },
            {
            "name": "Server Setup", 
            "slug": "server-setup",
            "category": hardware, 
            "price": "250000.00",
            "description": "Server installation and configuration",
            "tags": [tag_enterprise]
            },
            {
            "name": "Cloud Backup", 
            "slug": "cloud-backup",
            "category": services, 
            "price": "15000.00",
            "description": "Off-site cloud backup", 
            "tags": [tag_discount]
            },
            {
            "name": "IT Consulting", 
            "slug": "it-consulting",
            "category": consulting, 
            "price": "80000.00",
            "description": "IT infrastructure consulting", 
            "tags": []
            },
            {
            "name": "Support Plan Basic", 
            "slug": "support-plan-basic",
            "category": support, 
            "price": "25000.00",
            "description": "Basic support plan", 
            "tags": [tag_discount]
            },
            {
            "name": "Support Plan Premium", 
            "slug": "support-plan-premium",
            "category": support, 
            "price": "75000.00",
            "description": "24/7 premium support",
            "tags": [tag_vip, tag_enterprise]
            },
            {
            "name": "Mobile CRM App", 
            "slug": "mobile-crm-app",
            "category": software, 
            "price": "35000.00",
            "description": "Mobile CRM application", 
            "tags": [tag_enterprise, tag_vip]
            },
        ]
        for data in products_data:
            tags = data.pop("tags")
            product, created = Product.objects.get_or_create(
                slug=data["slug"],
                defaults={**data, "created_by": admin},
            )
            if created and tags:
                product.tags.set(tags)
        self.stdout.write(f"  Products:   {Product.objects.count()}")

    #  Deals 
    def _create_deals(self) -> None:
        """Seed deals across all four statuses, with realistic amounts."""
        clients = list(Client.objects.all())
        products = list(Product.objects.all())
        managers = list(self.User.objects.filter(is_staff=False))  # type: ignore[attr-defined]

        # Cycle through statuses so we get rows in every state.
        statuses: list[str] = [s.value for s in Deal.Status]
        titles: list[str] = [
            "CRM rollout", "License renewal", "Cloud backup activation",
            "IT consulting", "Hardware purchase", "Support renewal",
            "New enterprise contract", "Pilot project",
            "License expansion", "Technical maintenance",
        ]
        for i, title in enumerate(titles):
            client = clients[i % len(clients)]
            product = products[i % len(products)]
            manager = managers[i % len(managers)] if managers else None
            deal_status: str = statuses[i % len(statuses)]
            amount_multiplier = random.randint(*DEAL_AMOUNT_MULTIPLIER_RANGE)
            amount = float(product.price) * amount_multiplier
            closed_at = (
                timezone.now() - timedelta(days=random.randint(*DEAL_CLOSED_DAYS_AGO_RANGE))
                if deal_status in (Deal.Status.CLOSED_WON, Deal.Status.CLOSED_LOST)
                else None
            )

            Deal.objects.get_or_create(
                title=title,
                client=client,
                defaults={
                    "product": product,
                    "amount": amount,
                    "status": deal_status,
                    "closed_at": closed_at,
                    "created_by": manager,
                },
            )
        self.stdout.write(f"  Deals:      {Deal.objects.count()}")

    #  Tasks 
    def _create_tasks(self) -> None:
        """Seed tasks across all three statuses."""
        users = list(self.User.objects.all())  # type: ignore[attr-defined]
        deals = list(Deal.objects.all())
        clients = list(Client.objects.all())

        tasks_data: list[dict[str, str]] = [
            {"title": "Call the client to confirm requirements",
             "status": Task.Status.PENDING},
            {"title": "Prepare a commercial proposal",
             "status": Task.Status.IN_PROGRESS},
            {"title": "Run a product demo", "status": Task.Status.PENDING},
            {"title": "Get the contract approved by Legal",
             "status": Task.Status.IN_PROGRESS},
            {"title": "Send the invoice", "status": Task.Status.COMPLETED},
            {"title": "Install and configure the CRM",
             "status": Task.Status.PENDING},
            {"title": "Train the client's staff", "status": Task.Status.PENDING},
            {"title": "Verify payment status", "status": Task.Status.IN_PROGRESS},
            {"title": "Write the technical report", "status": Task.Status.COMPLETED},
            {"title": "Schedule a follow-up meeting", "status": Task.Status.PENDING},
            {"title": "Update client data in the system",
             "status": Task.Status.COMPLETED},
            {"title": "Audit the IT infrastructure",
             "status": Task.Status.IN_PROGRESS},
        ]
        for i, data in enumerate(tasks_data):
            assigned = users[i % len(users)]
            deal = deals[i % len(deals)] if deals else None
            client = clients[i % len(clients)]
            due_date = timezone.now() + timedelta(
                days=random.randint(*TASK_DUE_DAYS_AHEAD_RANGE),
            )

            Task.objects.get_or_create(
                title=data["title"],
                defaults={
                    "description": f"Description: {data['title']}",
                    "assigned_to": assigned,
                    "client": client,
                    "deal": deal,
                    "status": data["status"],
                    "due_date": due_date,
                },
            )
        self.stdout.write(f"  Tasks:      {Task.objects.count()}")

    #  Comments 
    def _create_comments(self) -> None:
        """Seed comments on the first few tasks and deals."""
        users = list(self.User.objects.all())  # type: ignore[attr-defined]
        tasks = list(Task.objects.all()[:COMMENTED_OBJECTS_LIMIT])
        deals = list(Deal.objects.all()[:COMMENTED_OBJECTS_LIMIT])

        ct_task = ContentType.objects.get_for_model(Task)
        ct_deal = ContentType.objects.get_for_model(Deal)

        task_comments: list[str] = [
            "Reached out to the client, waiting for a reply",
            "Documents have been sent for review",
            "Task completed successfully",
            "Need to clarify the details with the manager",
            "Pushed to next week",
        ]
        deal_comments: list[str] = [
            "Client is interested, continuing negotiations",
            "Proposal sent, awaiting feedback",
            "Deal is in the final approval stage",
            "Client requested a 10% discount",
            "Contract signed, awaiting payment",
        ]
        for i, task in enumerate(tasks):
            Comment.objects.get_or_create(
                content_type=ct_task,
                object_id=task.pk,
                author=users[i % len(users)],
                defaults={"body": task_comments[i]},
            )
        for i, deal in enumerate(deals):
            Comment.objects.get_or_create(
                content_type=ct_deal,
                object_id=deal.pk,
                author=users[i % len(users)],
                defaults={"body": deal_comments[i]},
            )
        self.stdout.write(f"  Comments:   {Comment.objects.count()}")

    #  Summary 
    def _print_summary(self) -> None:
        """Print final row counts and the demo credentials."""
        user_count = self.User.objects.count()  # type: ignore[attr-defined]
        self.stdout.write("\nDatabase totals:")
        self.stdout.write(f"   Users:      {self.User.objects.count()}")
        self.stdout.write(f"   Categories: {Category.objects.count()}")
        self.stdout.write(f"   Tags:       {Tag.objects.count()}")
        self.stdout.write(f"   Clients:    {Client.objects.count()}")
        self.stdout.write(f"   Products:   {Product.objects.count()}")
        self.stdout.write(f"   Deals:      {Deal.objects.count()}")
        self.stdout.write(f"   Tasks:      {Task.objects.count()}")
        self.stdout.write(f"   Comments:   {Comment.objects.count()}")
        self.stdout.write(f"\nDemo accounts (password: {DEMO_PASSWORD}):")
        self.stdout.write("   manager1@crm.com — manager (language: ru)")
        self.stdout.write("   manager2@crm.com — manager (language: kk)")
        self.stdout.write("   manager3@crm.com — manager (language: en)")
        self.stdout.write(f"   {STAFF_EMAIL}    — staff / admin")
