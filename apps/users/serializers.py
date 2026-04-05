from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer, TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=6)
    confirm_password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'phone_number', 'first_name',
            'last_name', 'role', 'password', 'confirm_password',
            'fixed_salary',
        )
        read_only_fields = ('id',)

    def validate(self, attrs):
        password = attrs.get('password')
        confirm_password = attrs.get('confirm_password')

        if password is not None:
            if password != confirm_password:
                raise serializers.ValidationError({"password": "The passwords did not match."})

        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password', None)

        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'phone_number', 'first_name', 'last_name', 'role')
        read_only_fields = ('id', 'role')


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(min_length=8, max_length=128, write_only=True,
                                         style={'input_type': 'password'})
    new_password = serializers.CharField(min_length=8, max_length=128, write_only=True,
                                         style={'input_type': 'password'})
    confirm_new_password = serializers.CharField(min_length=8, max_length=128, write_only=True,
                                                 style={'input_type': 'password'})

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("The old password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_new_password']:
            raise serializers.ValidationError({
                'password': "The new password fields did not match."
            })
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError({
                'password': "The new password must be different from the old one."
            })

        try:
            validate_password(attrs['new_password'], user=self.context['request'].user)
        except ValidationError as e:
            raise serializers.ValidationError({'password': e.messages})

        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data: dict = super().validate(attrs)

        user = self.user

        data["user"] = {
            "id": user.id,
            "username": user.username,
            "phone_number": user.phone_number,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
        }

        return data


class MyTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        data: dict = super().validate(attrs)

        refresh = RefreshToken(attrs["refresh"])
        user_id = refresh.get("user_id")

        try:
            user = User.objects.get(id=user_id)
            data["user"] = {
                "id": user.id,
                "username": user.username,
                "phone_number": user.phone_number,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
            }
        except User.DoesNotExist:
            pass

        return data
