from django.db import models

# Create your models here.
class Stock(models.Model):
    name = models.CharField(max_length=40, default='')
    code = models.CharField(max_length=40, default='')
    sector = models.CharField(max_length=100, default='')


class Price(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    date = models.DateField()
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.PositiveIntegerField()
