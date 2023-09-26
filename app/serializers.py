from rest_framework import serializers
from app.models import Price, Stock

class FinancialDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = Price
        fields = '__all__'


class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = '__all__'