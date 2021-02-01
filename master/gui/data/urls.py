from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('getTradeable', views.getTradeable, name='getTradeable'),
    path('putTrading', views.putTrading, name='putTrading'),
    path('viewTrading', views.viewTrading, name='viewTrading')
]