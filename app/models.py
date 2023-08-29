from django.db import models

# Create your models here.
class Price(models.Model):
    code = models.CharField(max_length=20, default='')
    date = models.DateField()
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.PositiveIntegerField()
