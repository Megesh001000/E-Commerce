from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import BasePermission
from rest_framework import status
from rest_framework.pagination import PageNumberPagination

from decimal import Decimal ,InvalidOperation

from .models import Product
from .permissions import IsStaffUser
from .serializer import ProductSerializer



class ProductListAPI(APIView):
    permission_classes=[IsStaffUser]
    def get(self,request):
        products=Product.objects.all()
        
        search=request.query_params.get("search","").strip() #Search Filter
        if len(search)>100:
            return Response(
                 {"error": "Search must be 100 characters or fewer."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if search:
            products=products.filter(
                Q(name__icontains=search)|Q(description__icontains=search)
            )

        category=request.query_params.get("category","").strip()    #Category Filter
        if  category:
            products=products.filter(category__slug__iexact=category)

        brand=request.query_params.get("brand","").strip() #Brand Filter
        if brand:
            products=products.filter(brand__slug__iexact=brand)

        min_price=request.query_params.get("min_price")  #Price Filtering  Minimum
        max_price=request.query_params.get("max_price")  #Price Filtering  Maximum

        try:    #checks for decimal
            min_value=Decimal(min_price) if min_price else None
            max_value=Decimal(max_price) if max_price else None
        except InvalidOperation:
            return Response(
                {"error": "Prices must be valid numbers."},
                status=status.HTTP_400_BAD_REQUEST
            )   

        
        if (           
            (min_value is not None and min_value <=0) or (max_value is not None and max_value <=0 )
        ):  #check for number is not negative or 0
            return Response(
                {"error": "Prices cannot be negative."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if (
            min_value is  not None and max_value is not None and min_value>max_value
        ): # checks for min is less then max
            return Response(
                {"error": "Minimum price cannot exceed maximum price."},
                status=status.HTTP_400_BAD_REQUEST
             )

        if min_value:
            products=products.filter(price__gte=min_value)
        if max_value:
            products=products.filter(price__lte=max_price)


        in_stock=request.query_params.get("in_stock")

        if in_stock is not None:
            if in_stock.lower()=="true":
                products=products.filter(stock__gt=0)
            elif in_stock.lower()=="false":
                products=products.filter(stock=0)
            else:
                return Response(
                    {"error": "in_stock must be true or false."},
                    status=status.HTTP_400_BAD_REQUEST
                )


        ordering=request.query_params.get("ordering","-created_at")  #Sorting  Default sorting 

        allowed_orderings=[
            "price","-price","created_at","-created_at","name","-name"  #allowed sortings
        ]

        if ordering not  in allowed_orderings:
            return Response(
                {"error": "Invalid ordering parameter."},
                status=status.HTTP_400_BAD_REQUEST
            )

        products=products.order_by(ordering,"id")
        



        paginator=PageNumberPagination()   #Pagination
        paginator.page_size=10
        page=paginator.paginate_queryset(products,request,view=self)

        serializer=ProductSerializer(page,many=True)
        return paginator.get_paginated_response(serializer.data)
    def post(self,request):
        serializer=ProductSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
                        serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST
            )

class ProductDetailAPI(APIView):
    permission_classes=[IsStaffUser]

    def get(self,request,pk):
        product=get_object_or_404(Product,pk=pk)
        serializer=ProductSerializer(product)

        return Response(serializer.data)

    def patch(self,request,pk):
        product=get_object_or_404(Product,pk=pk)

        serializer=ProductSerializer(product,data=request.data,partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
        )

    def put(self,request,pk):
        product=get_object_or_404(Product,pk=pk)
        serializer=ProductSerializer(product,data=request.data)

        if serializer.is_valid():
            serializer.save()
            return  Response(
                serializer.data
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    def  delete(self,request,pk):
        product=get_object_or_404(Product,pk=pk)
        product.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )