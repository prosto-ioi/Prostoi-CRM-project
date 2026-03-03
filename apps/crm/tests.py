from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APIClient
from rest_framework import status

from .models import Category, Tag, Client, Product, Deal, Task, Comment

User = get_user_model()


class BaseTestCase(TestCase):

    def setUp(self):
        self.client_api = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            first_name='Aliko',
            last_name='Test',
            password='StrongPass123!',
        )
        self.client_api.force_authenticate(user=self.user)


# ══════════════════════════════════════════════════════
#  Category
# ══════════════════════════════════════════════════════
class CategoryTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.payload = {
            'name_en': 'Software',
            'name_ru': 'Программы',
            'name_kk': 'Бағдарламалар',
        }

    # ── CREATE ────────────────────────────────────────
    def test_create_category(self):
        res = self.client_api.post('/api/crm/categories/', self.payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['name_en'], 'Software')
        self.assertEqual(res.data['slug'], 'software')

    # ── LIST ──────────────────────────────────────────
    def test_list_categories(self):
        Category.objects.create(name_en='Software', slug='software')
        Category.objects.create(name_en='Hardware', slug='hardware')
        res = self.client_api.get('/api/crm/categories/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    # ── RETRIEVE ──────────────────────────────────────
    def test_retrieve_category(self):
        Category.objects.create(name_en='Software', slug='software')
        res = self.client_api.get('/api/crm/categories/software/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['name_en'], 'Software')

    # ── UPDATE (PUT) ──────────────────────────────────
    def test_update_category(self):
        Category.objects.create(name_en='Software', slug='software')
        res = self.client_api.put('/api/crm/categories/software/', {
            'name_en': 'Software Updated',
            'name_ru': 'Обновлено',
            'name_kk': 'Жаңартылды',
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['name_en'], 'Software Updated')

    # ── PARTIAL UPDATE (PATCH) ────────────────────────
    def test_patch_category(self):
        Category.objects.create(name_en='Software', slug='software')
        res = self.client_api.patch('/api/crm/categories/software/', {
            'name_ru': 'ПО',
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['name_ru'], 'ПО')

    # ── DELETE ────────────────────────────────────────
    def test_delete_category(self):
        Category.objects.create(name_en='Software', slug='software')
        res = self.client_api.delete('/api/crm/categories/software/')
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Category.objects.count(), 0)

    # ── AUTH REQUIRED ─────────────────────────────────
    def test_unauthenticated_rejected(self):
        self.client_api.force_authenticate(user=None)
        res = self.client_api.get('/api/crm/categories/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


# ══════════════════════════════════════════════════════
#  Tag
# ══════════════════════════════════════════════════════
class TagTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.payload = {'name': 'urgent'}

    def test_create_tag(self):
        res = self.client_api.post('/api/crm/tags/', self.payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['name'], 'urgent')
        self.assertEqual(res.data['slug'], 'urgent')

    def test_list_tags(self):
        Tag.objects.create(name='urgent', slug='urgent')
        Tag.objects.create(name='low', slug='low')
        res = self.client_api.get('/api/crm/tags/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_retrieve_tag(self):
        Tag.objects.create(name='urgent', slug='urgent')
        res = self.client_api.get('/api/crm/tags/urgent/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_update_tag(self):
        Tag.objects.create(name='urgent', slug='urgent')
        res = self.client_api.put('/api/crm/tags/urgent/', {'name': 'critical'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['name'], 'critical')

    def test_patch_tag(self):
        Tag.objects.create(name='urgent', slug='urgent')
        res = self.client_api.patch('/api/crm/tags/urgent/', {'name': 'high'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['name'], 'high')

    def test_delete_tag(self):
        Tag.objects.create(name='urgent', slug='urgent')
        res = self.client_api.delete('/api/crm/tags/urgent/')
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Tag.objects.count(), 0)


# ══════════════════════════════════════════════════════
#  Client
# ══════════════════════════════════════════════════════
class ClientTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.payload = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'phone': '+77001234567',
            'address': 'Almaty, Kazakhstan',
        }

    def test_create_client(self):
        res = self.client_api.post('/api/crm/clients/', self.payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['email'], 'john@example.com')

    def test_list_clients(self):
        Client.objects.create(**self.payload)
        res = self.client_api.get('/api/crm/clients/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_retrieve_client(self):
        c = Client.objects.create(**self.payload)
        res = self.client_api.get(f'/api/crm/clients/{c.id}/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['first_name'], 'John')

    def test_update_client(self):
        c = Client.objects.create(**self.payload)
        updated = self.payload.copy()
        updated['first_name'] = 'Jane'
        res = self.client_api.put(f'/api/crm/clients/{c.id}/', updated)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['first_name'], 'Jane')

    def test_patch_client(self):
        c = Client.objects.create(**self.payload)
        res = self.client_api.patch(f'/api/crm/clients/{c.id}/', {'phone': '+77009999999'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['phone'], '+77009999999')

    def test_delete_client(self):
        c = Client.objects.create(**self.payload)
        res = self.client_api.delete(f'/api/crm/clients/{c.id}/')
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Client.objects.count(), 0)

    def test_duplicate_email_rejected(self):
        Client.objects.create(**self.payload)
        res = self.client_api.post('/api/crm/clients/', self.payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


# ══════════════════════════════════════════════════════
#  Product
# ══════════════════════════════════════════════════════
class ProductTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.category = Category.objects.create(name_en='Software', slug='software')
        self.tag = Tag.objects.create(name='urgent', slug='urgent')
        self.payload = {
            'name': 'CRM License',
            'category': self.category.id,
            'tags': [self.tag.id],
            'price': '99.99',
            'description': 'Annual CRM license',
        }

    def test_create_product(self):
        res = self.client_api.post('/api/crm/products/', self.payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['name'], 'CRM License')
        self.assertEqual(res.data['slug'], 'crm-license')
        self.assertEqual(res.data['category_detail']['name_en'], 'Software')

    def test_list_products(self):
        Product.objects.create(
            name='CRM License', slug='crm-license',
            category=self.category, price='99.99',
        )
        res = self.client_api.get('/api/crm/products/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_retrieve_product(self):
        Product.objects.create(
            name='CRM License', slug='crm-license',
            category=self.category, price='99.99',
        )
        res = self.client_api.get('/api/crm/products/crm-license/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_update_product(self):
        Product.objects.create(
            name='CRM License', slug='crm-license',
            category=self.category, price='99.99',
        )
        updated = self.payload.copy()
        updated['price'] = '149.99'
        res = self.client_api.put('/api/crm/products/crm-license/', updated)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['price'], '149.99')

    def test_patch_product(self):
        Product.objects.create(
            name='CRM License', slug='crm-license',
            category=self.category, price='99.99',
        )
        res = self.client_api.patch('/api/crm/products/crm-license/', {'in_stock': False})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data['in_stock'])

    def test_delete_product(self):
        Product.objects.create(
            name='CRM License', slug='crm-license',
            category=self.category, price='99.99',
        )
        res = self.client_api.delete('/api/crm/products/crm-license/')
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Product.objects.count(), 0)


# ══════════════════════════════════════════════════════
#  Deal
# ══════════════════════════════════════════════════════
class DealTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.crm_client = Client.objects.create(
            first_name='John', last_name='Doe',
            email='john@example.com',
        )
        self.category = Category.objects.create(name_en='Software', slug='software')
        self.product = Product.objects.create(
            name='CRM License', slug='crm-license',
            category=self.category, price='99.99',
        )
        self.payload = {
            'client': self.crm_client.id,
            'product': self.product.id,
            'title': 'CRM Sale to John',
            'amount': '99.99',
            'status': 'new',
        }

    def test_create_deal(self):
        res = self.client_api.post('/api/crm/deals/', self.payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['title'], 'CRM Sale to John')
        self.assertEqual(res.data['client_detail']['email'], 'john@example.com')

    def test_list_deals(self):
        Deal.objects.create(
            client=self.crm_client, product=self.product,
            title='Sale', amount='99.99',
        )
        res = self.client_api.get('/api/crm/deals/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_retrieve_deal(self):
        d = Deal.objects.create(
            client=self.crm_client, title='Sale', amount='99.99',
        )
        res = self.client_api.get(f'/api/crm/deals/{d.id}/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_update_deal(self):
        d = Deal.objects.create(
            client=self.crm_client, title='Sale', amount='99.99',
        )
        updated = self.payload.copy()
        updated['status'] = 'in_progress'
        res = self.client_api.put(f'/api/crm/deals/{d.id}/', updated)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], 'in_progress')

    def test_patch_deal(self):
        d = Deal.objects.create(
            client=self.crm_client, title='Sale', amount='99.99',
        )
        res = self.client_api.patch(f'/api/crm/deals/{d.id}/', {'status': 'closed_won'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], 'closed_won')

    def test_delete_deal(self):
        d = Deal.objects.create(
            client=self.crm_client, title='Sale', amount='99.99',
        )
        res = self.client_api.delete(f'/api/crm/deals/{d.id}/')
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Deal.objects.count(), 0)

    def test_invalid_status_rejected(self):
        payload = self.payload.copy()
        payload['status'] = 'invalid_status'
        res = self.client_api.post('/api/crm/deals/', payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


# ══════════════════════════════════════════════════════
#  Task
# ══════════════════════════════════════════════════════
class TaskTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.crm_client = Client.objects.create(
            first_name='John', last_name='Doe',
            email='john@example.com',
        )
        self.deal = Deal.objects.create(
            client=self.crm_client, title='Sale', amount='99.99',
        )
        self.payload = {
            'title': 'Follow up with John',
            'description': 'Call about the deal',
            'assigned_to': self.user.id,
            'client': self.crm_client.id,
            'deal': self.deal.id,
            'status': 'pending',
        }

    def test_create_task(self):
        res = self.client_api.post('/api/crm/tasks/', self.payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['title'], 'Follow up with John')

    def test_list_tasks(self):
        Task.objects.create(title='Task 1', assigned_to=self.user)
        res = self.client_api.get('/api/crm/tasks/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_retrieve_task(self):
        t = Task.objects.create(title='Task 1', assigned_to=self.user)
        res = self.client_api.get(f'/api/crm/tasks/{t.id}/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_update_task(self):
        t = Task.objects.create(title='Task 1', assigned_to=self.user)
        updated = self.payload.copy()
        updated['title'] = 'Updated task'
        res = self.client_api.put(f'/api/crm/tasks/{t.id}/', updated)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['title'], 'Updated task')

    def test_patch_task(self):
        t = Task.objects.create(title='Task 1', assigned_to=self.user)
        res = self.client_api.patch(f'/api/crm/tasks/{t.id}/', {'status': 'completed'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], 'completed')

    def test_delete_task(self):
        t = Task.objects.create(title='Task 1', assigned_to=self.user)
        res = self.client_api.delete(f'/api/crm/tasks/{t.id}/')
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Task.objects.count(), 0)


# ══════════════════════════════════════════════════════
#  Comment (GenericForeignKey)
# ══════════════════════════════════════════════════════
class CommentTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.crm_client = Client.objects.create(
            first_name='John', last_name='Doe',
            email='john@example.com',
        )
        self.deal = Deal.objects.create(
            client=self.crm_client, title='Sale', amount='99.99',
        )
        self.task = Task.objects.create(
            title='Task 1', assigned_to=self.user,
        )

    def test_create_comment_on_deal(self):
        res = self.client_api.post('/api/crm/comments/', {
            'content_type': 'deal',
            'object_id': self.deal.id,
            'body': 'Initial contact made',
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['body'], 'Initial contact made')

    def test_create_comment_on_task(self):
        res = self.client_api.post('/api/crm/comments/', {
            'content_type': 'task',
            'object_id': self.task.id,
            'body': 'Working on it',
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_list_comments(self):
        ct = ContentType.objects.get_for_model(Deal)
        Comment.objects.create(
            author=self.user, content_type=ct,
            object_id=self.deal.id, body='Test',
        )
        res = self.client_api.get('/api/crm/comments/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_filter_comments_by_target(self):
        ct_deal = ContentType.objects.get_for_model(Deal)
        ct_task = ContentType.objects.get_for_model(Task)
        Comment.objects.create(
            author=self.user, content_type=ct_deal,
            object_id=self.deal.id, body='Deal comment',
        )
        Comment.objects.create(
            author=self.user, content_type=ct_task,
            object_id=self.task.id, body='Task comment',
        )
        res = self.client_api.get('/api/crm/comments/?target=deal')
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['body'], 'Deal comment')

    def test_delete_comment(self):
        ct = ContentType.objects.get_for_model(Deal)
        c = Comment.objects.create(
            author=self.user, content_type=ct,
            object_id=self.deal.id, body='Test',
        )
        res = self.client_api.delete(f'/api/crm/comments/{c.id}/')
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Comment.objects.count(), 0)

    def test_invalid_content_type_rejected(self):
        res = self.client_api.post('/api/crm/comments/', {
            'content_type': 'nonexistent',
            'object_id': 1,
            'body': 'Should fail',
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)