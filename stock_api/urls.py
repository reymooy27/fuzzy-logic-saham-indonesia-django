"""
URL configuration for stock_api project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from app.views import api_view, get_stock_data, scraping_single_stock, get_all_data, scraping,  upload_csv
from django.urls import path

urlpatterns = [
    path("api/saham/all", get_all_data),
    path("admin", admin.site.urls),
    path("api/saham", api_view),
    path("api/saham/<str:code>", get_stock_data),
    path('api/scraping', scraping),
    path('api/scraping/<str:code>', scraping_single_stock),
    path('api/create', upload_csv),
]
