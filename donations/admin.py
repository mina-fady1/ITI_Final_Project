from django.contrib import admin
from .models import Donation


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ['user', 'project', 'amount_display', 'created_at']
    list_filter = ['created_at', 'project']
    search_fields = ['user__email', 'user__first_name', 'project__title']

    @admin.display(description='Amount (EGP)')
    def amount_display(self, obj):
        return f"{obj.amount} EGP"
