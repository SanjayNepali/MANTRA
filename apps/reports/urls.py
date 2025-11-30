# apps/reports/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_report, name='create_report'),
    path('my-reports/', views.my_reports, name='my_reports'),
    path('admin/', views.admin_reports_dashboard, name='admin_reports_dashboard'),
]