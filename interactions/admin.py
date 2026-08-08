from django.contrib import admin
from .models import Comment, Rating, Report


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'project', 'parent', 'content_snippet', 'created_at']
    list_filter = ['created_at', 'project']
    search_fields = ['user__email', 'content', 'project__title']

    @admin.display(description='Content')
    def content_snippet(self, obj):
        return obj.content[:50]


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['user', 'project', 'value', 'created_at']
    list_filter = ['value', 'created_at']
    search_fields = ['user__email', 'project__title']


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['user', 'target_display', 'reason_snippet', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__email', 'reason', 'project__title']
    actions = ['mark_as_reviewed', 'mark_as_pending']

    @admin.display(description='Reported Target')
    def target_display(self, obj):
        if obj.project:
            return f"Project: {obj.project.title}"
        elif obj.comment:
            return f"Comment ID #{obj.comment.id}"
        return "Unknown"

    @admin.display(description='Reason')
    def reason_snippet(self, obj):
        return obj.reason[:60]

    @admin.action(description='Mark selected reports as Reviewed')
    def mark_as_reviewed(self, request, queryset):
        queryset.update(status='reviewed')

    @admin.action(description='Mark selected reports as Pending')
    def mark_as_pending(self, request, queryset):
        queryset.update(status='pending')
