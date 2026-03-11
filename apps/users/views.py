import logging
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiExample
from .serializers import (
    UserRegistrationSerializer, UserResponseSerializer, CustomTokenObtainPairSerializer
)

logger = logging.getLogger(__name__)


class RegistrationView(generics.CreateAPIView):

    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]


    @extend_schema(
        summary='Регистрация пользователя',
        description=('Создаёт нового пользователя и возвращает пару JWT токенов.\n\n'
                     'Не требует аутентификации.\n\n'
                     '**Поля:** email, first_name, last_name, password, password2, language, timezone'),
        tags=['Auth'],
        request=UserRegistrationSerializer,
        responses={201: UserRegistrationSerializer, 400: None, },
        examples=[
            OpenApiExample(
                'Пример запроса',
                value={
                    'email': 'user@gmail.com',
                    'first_name': 'Алихан',
                    'last_name': 'Сейткали',
                    'password': 'StrongPass123!',
                    'password2': 'StrongPass123!',
                    'language': 'ru',
                    'timezone': 'Asia/Almaty',
                },
                request_only=True,
            ),
        ],

    )
    def create(self, request, *args, **kwargs):
        email = request.data.get('email', '')
        logger.info(f'Registration attempt: {email}')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        logger.info(f'Registration successful: {email}')

        response_data = {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserResponseSerializer(user).data
        }
        return Response(response_data, status=status.HTTP_201_CREATED)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


    @extend_schema(
        summary='Получить токены (логин)',
        description=(
            'Принимает email и пароль, возвращает access и refresh токены.\n\n'
            'Не требует аутентификации.'
        ),
        tags=['Auth'],
        responses={
            200: CustomTokenObtainPairSerializer,
            400: None,
            401: None,
        },
        examples=[
            OpenApiExample(
                'Пример запроса',
                value={'email': 'user@example.com', 'password': 'StrongPass123!'},
                request_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        email = request.data.get('email', '')
        logger.info(f'Login attempt: {email}')
        try:
            response = super().post(request, *args, **kwargs)
            if response.status_code == 200:
                logger.info(f'Login successful: {email}')
            else:
                logger.warning(f'Login failed: {email}')
            return response
        except Exception as e:
            logger.error(f'Login error: {email}, {str(e)}')
            raise


class CustomTokenRefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary='Обновить access токен',
        description='Принимает refresh токен, возвращает новый access токен.',
        tags=['Auth'],
        responses={200: None, 400: None, 401: None},
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)