from django.shortcuts import render

# Create your views here.
# apps/reports/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse

from .models import Report, ModerationAction
from .forms import ReportForm

@login_required
def create_report(request):
    """Create a new report"""
    if request.method == 'POST':
        form = ReportForm(request.POST, request.FILES)
        
        if form.is_valid():
            report = form.save(commit=False)
            report.reported_by = request.user
            report.save()
            
            messages.success(request, 'Report submitted successfully')
            return redirect('dashboard')
    else:
        # Pre-fill based on query params
        report_type = request.GET.get('type')
        target_id = request.GET.get('target')
        
        form = ReportForm(initial={
            'report_type': report_type,
            'target_object_id': target_id
        })
    
    return render(request, 'reports/create.html', {'form': form})


@login_required
def my_reports(request):
    """View user's submitted reports"""
    reports = Report.objects.filter(
        reported_by=request.user
    ).order_by('-created_at')
    
    return render(request, 'reports/my_reports.html', {'reports': reports})


@login_required
def admin_reports_dashboard(request):
    """Admin dashboard for reports"""
    if request.user.user_type not in ['admin', 'subadmin']:
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    pending_reports = Report.objects.filter(status='pending').count()
    reviewing_reports = Report.objects.filter(status='reviewing').count()
    
    recent_reports = Report.objects.filter(
        status__in=['pending', 'reviewing']
    ).order_by('-created_at')[:10]
    
    context = {
        'pending_reports': pending_reports,
        'reviewing_reports': reviewing_reports,
        'recent_reports': recent_reports
    }
    
    return render(request, 'reports/admin_dashboard.html', context)