from django.contrib import admin

# Register your models here.
from app.models import Price, Stock

admin.site.register(Price)
admin.site.register(Stock)