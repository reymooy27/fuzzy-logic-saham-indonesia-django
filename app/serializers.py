from rest_framework import serializers
from app.models import Price

class FinancialDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = Price
        fields = '__all__'
