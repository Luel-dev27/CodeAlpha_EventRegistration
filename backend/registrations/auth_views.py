from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from rest_framework import serializers, status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .throttles import LoginThrottle, SignupThrottle

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        min_length=8,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")
        read_only_fields = ("id",)

    def validate_email(self, value):
        if value and User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        candidate = User(
            username=attrs.get("username", ""), email=attrs.get("email", "")
        )
        try:
            validate_password(attrs["password"], candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class RegisterView(APIView):
    throttle_classes = (SignupThrottle,)
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                "user": {"id": user.id, "username": user.username, "email": user.email},
                "token": token.key,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(
        write_only=True, trim_whitespace=False, style={"input_type": "password"}
    )


class LoginView(APIView):
    throttle_classes = (LoginThrottle,)
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(request=request, **serializer.validated_data)
        if user is None:
            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                "user": {"id": user.id, "username": user.username, "email": user.email},
                "token": token.key,
            }
        )


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        request.auth.delete()
        return Response(
            {"detail": "Successfully logged out."}, status=status.HTTP_200_OK
        )
