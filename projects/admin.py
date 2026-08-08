from django.contrib import admin
from .models import Category, Tag, Project, ProjectImage


class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['title', 'creator', 'category', 'target', 'total_donations_display', 'status_display', 'is_featured', 'is_cancelled', 'created_at']
    list_filter = ['is_featured', 'is_cancelled', 'category', 'created_at', 'start_time', 'end_time']
    search_fields = ['title', 'details', 'creator__email', 'creator__first_name', 'creator__last_name']
    inlines = [ProjectImageInline]
    actions = ['make_featured', 'remove_featured']

    @admin.display(description='Total Raised (EGP)')
    def total_donations_display(self, obj):
        return f"{obj.total_donations} EGP"

    @admin.display(description='Status')
    def status_display(self, obj):
        return obj.status

    @admin.action(description='Mark selected projects as Featured')
    def make_featured(self, request, queryset):
        queryset.update(is_featured=True)

    @admin.action(description='Remove Featured status from selected projects')
    def remove_featured(self, request, queryset):
        queryset.update(is_featured=False)
