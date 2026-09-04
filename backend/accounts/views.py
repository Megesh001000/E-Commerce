from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .serializer import RegisterSerializer,LoginSerializer


class RegisterAPI(APIView):
    def post(self,request):
        serializer=RegisterSerializer(data=request.data)


        if serializer.is_valid():
            serializer.save()


            return Response(
                {
                    "message":"User Logged in successfully"
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)


class LoginAPI(APIView):
    def post(self,request):
        serializer=LoginSerializer(data=request.data)

        if serializer.is_valid():
            return Response(serializer.validated_data)
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)


class ProfileAPI(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        return Response(
            {
                "username":request.user.username,
                "email":request.user.email,
             }
        )