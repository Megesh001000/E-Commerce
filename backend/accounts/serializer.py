from .models import User
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation  import validate_password
from django.core.exceptions import ValidationError as  DjangoValidationError
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields=["username","email","password"]
        extra_kwargs={"password":{"write_only":True}}

    def validate(self,attrs):
        user=User(
            username=attrs.get("username"),
            email=attrs.get("email","")
        )
        try:
            validate_password(
                attrs["password"],
                user=user
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError({
                "password": error.messages
            })
        return attrs
    def create(self,validated_data):
        return User.objects.create_user(**validated_data)

class LoginSerializer(serializers.Serializer):
    username=serializers.CharField()
    password=serializers.CharField(write_only=True)

    def validate(self,attrs):
        username=attrs.get("username")
        password=attrs.get("password")
        request=self.context.get("request")
        user=authenticate(
            request=request,username=username,password=password
        )
        if user is None:
            raise serializers.ValidationError("Invalid username or password")

        refresh=RefreshToken.for_user(user)

        return{
            "access":str(refresh.access_token),
            "refresh":str(refresh)
        }

