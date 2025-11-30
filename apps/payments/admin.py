# apps/payments/admin.py

from django.contrib import admin
from django.utils import timezone
from .models import (
    PaymentTransaction, PaymentMethod, PaymentDispute
)

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'user', 'amount', 'payment_type',
                   'payment_method', 'status', 'created_at', 'completed_at']
    list_filter = ['payment_type', 'payment_method', 'status', 'created_at']
    search_fields = ['transaction_id', 'reference_id', 'user__username']
    readonly_fields = ['transaction_id', 'created_at', 'completed_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Payment Details', {
            'fields': ('amount', 'payment_type', 'payment_method')
        }),
        ('Transaction Info', {
            'fields': ('transaction_id', 'reference_id', 'status')
        }),
        ('Related Object', {
            'fields': ('related_object_type', 'related_object_id'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_completed', 'mark_as_failed', 'mark_as_refunded']

    def mark_as_completed(self, request, queryset):
        now = timezone.now()
        updated = queryset.filter(status='pending').update(status='completed', completed_at=now)
        self.message_user(request, f'{updated} transaction(s) marked as completed.')
    mark_as_completed.short_description = 'Mark as Completed'

    def mark_as_failed(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='failed')
        self.message_user(request, f'{updated} transaction(s) marked as failed.')
    mark_as_failed.short_description = 'Mark as Failed'

    def mark_as_refunded(self, request, queryset):
        updated = queryset.filter(status='completed').update(status='refunded')
        self.message_user(request, f'{updated} transaction(s) refunded.')
    mark_as_refunded.short_description = 'Refund Transactions'


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['user', 'method_type', 'account_name', 'account_number_masked',
                   'is_default', 'is_active', 'created_at']
    list_filter = ['method_type', 'is_default', 'is_active', 'created_at']
    search_fields = ['user__username', 'account_name', 'account_number']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Payment Method Info', {
            'fields': ('method_type', 'account_number', 'account_name')
        }),
        ('Settings', {
            'fields': ('is_default', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )

    actions = ['set_as_default', 'activate_methods', 'deactivate_methods']

    def account_number_masked(self, obj):
        """Display masked account number for security"""
        if len(obj.account_number) > 4:
            return '*' * (len(obj.account_number) - 4) + obj.account_number[-4:]
        return obj.account_number
    account_number_masked.short_description = 'Account Number'

    def set_as_default(self, request, queryset):
        for method in queryset:
            # Remove default from other methods for this user
            PaymentMethod.objects.filter(user=method.user).update(is_default=False)
            method.is_default = True
            method.save()
        self.message_user(request, f'{queryset.count()} payment method(s) set as default.')
    set_as_default.short_description = 'Set as Default'

    def activate_methods(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} payment method(s) activated.')
    activate_methods.short_description = 'Activate Methods'

    def deactivate_methods(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} payment method(s) deactivated.')
    deactivate_methods.short_description = 'Deactivate Methods'


@admin.register(PaymentDispute)
class PaymentDisputeAdmin(admin.ModelAdmin):
    list_display = ['transaction', 'reason', 'status', 'created_at', 'resolved_at', 'resolved_by']
    list_filter = ['status', 'created_at']
    search_fields = ['transaction__transaction_id', 'reason', 'description']
    readonly_fields = ['created_at', 'resolved_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Dispute Info', {
            'fields': ('transaction', 'reason', 'description', 'status')
        }),
        ('Resolution', {
            'fields': ('resolution', 'resolved_by', 'resolved_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_investigating', 'mark_as_resolved', 'mark_as_closed']

    def mark_as_investigating(self, request, queryset):
        updated = queryset.update(status='investigating')
        self.message_user(request, f'{updated} dispute(s) marked as investigating.')
    mark_as_investigating.short_description = 'Mark as Investigating'

    def mark_as_resolved(self, request, queryset):
        now = timezone.now()
        updated = queryset.update(status='resolved', resolved_by=request.user, resolved_at=now)
        self.message_user(request, f'{updated} dispute(s) resolved.')
    mark_as_resolved.short_description = 'Mark as Resolved'

    def mark_as_closed(self, request, queryset):
        updated = queryset.update(status='closed')
        self.message_user(request, f'{updated} dispute(s) closed.')
    mark_as_closed.short_description = 'Close Disputes'