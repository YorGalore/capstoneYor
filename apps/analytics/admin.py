from django.contrib import admin

from .models import (
    Alert, AlertRule, Author, Category, Coalition, Issue, IssueLabel, IssueMergeHistory,
    LabelCorrection, Mention, PoliticalIssue, SubCategory,
)

admin.site.register(Coalition)
admin.site.register(PoliticalIssue)
admin.site.register(Mention)
admin.site.register(AlertRule)
admin.site.register(Alert)
admin.site.register(Author)
admin.site.register(Category)
admin.site.register(SubCategory)
admin.site.register(Issue)
admin.site.register(IssueLabel)
admin.site.register(IssueMergeHistory)


@admin.register(LabelCorrection)
class LabelCorrectionAdmin(admin.ModelAdmin):
    """Correction history is an audit record — read-only in the admin."""

    list_display = ("mention", "field", "old_value", "new_value", "corrected_by", "corrected_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
