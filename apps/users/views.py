import logging
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import (
    UserRegistrationSerializer, UserResponseSerializer, CustomTokenObtainPairSerializer
)

logger = logging.getLogger(__name__)


class RegistrationView(generics.CreateAPIView):

    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

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