# apps/analytics/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Analytics-specific routes only
    # Admin and SubAdmin dashboards moved to their respective apps

    # Report generation
    path('reports/generate/', views.generate_report, name='analytics_generate_report'),
    path('reports/export/', views.export_report, name='analytics_export_report'),
]