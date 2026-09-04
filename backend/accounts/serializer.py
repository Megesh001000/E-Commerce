from .models import User
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields=["username","email","password"]
        extra_kwargs={"password":{"write_only":True}}

    def create(self,validated_data):
        return User.objects.create_user(**validated_data)

class LoginSerializer(serializers.Serializer):
    username=serializers.CharField()
    password=serializers.CharField(write_only=True)

    def validate(self,attrs):
        username=attrs.get("username")
        password=attrs.get("password")
        user=authenticate(
            username=username,password=password
        )
        if user is None:
            raise serializers.ValidationError("Invalid username or password")

        refresh=RefreshToken.for_user(user)

        return{
            "access":str(refresh.access_token),
            "refresh":str(refresh)
        }

