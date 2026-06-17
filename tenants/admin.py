from django.contrib import admin
from .models import Tenant, TenantMember


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display        = ['name', 'slug', 'owner', 'is_active', 'created_at']
    list_filter         = ['is_active']
    search_fields       = ['name', 'slug', 'owner__username']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(TenantMember)
class TenantMemberAdmin(admin.ModelAdmin):
    list_display  = ['user', 'tenant', 'role', 'is_active', 'created_at']
    list_filter   = ['role', 'is_active', 'tenant']
    search_fields = ['user__username', 'user__email', 'tenant__name']
    raw_id_fields = ['user', 'tenant']
