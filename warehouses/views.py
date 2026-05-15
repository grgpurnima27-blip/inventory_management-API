from rest_framework import viewsets
from django.shortcuts import render

# Create your views here.
from .models import Warehouse
from .serializers import WarehouseSerializer

class WarehouseViewSet(viewsets.ModelViewSet):
    queryset= Warehouse.objects.all()