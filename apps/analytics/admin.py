from django.contrib import admin

from .models import (
    ActorSentimentAssessment, Alert, AlertRule, Author, Camp, Category, Coalition, DailyBrief, DailyBriefIssue,
    DailyBriefRun, GovernmentProgram, Issue, IssueLabel, IssueMergeHistory, LabelCorrection,
    Mention, PoliticalActor, PoliticalIssue, ResponseAction, SubCategory,
)

admin.site.register(Coalition)
admin.site.register(PoliticalIssue)
admin.site.register(Mention)
@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "condition_type", "channel", "is_active")
    list_filter = ("project", "condition_type", "channel", "is_active")


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "severity", "status", "triggered_at")
    list_filter = ("project", "severity", "status")
    list_select_related = ("project", "rule")
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

admin.site.register(Camp)
admin.site.register(PoliticalActor)
admin.site.register(ActorSentimentAssessment)
admin.site.register(GovernmentProgram)
admin.site.register(ResponseAction)
admin.site.register(DailyBriefRun)


@admin.register(DailyBrief)
class DailyBriefAdmin(admin.ModelAdmin):
    list_display = ("brief_date", "project", "status", "finalized_by", "finalized_at")

    def has_change_permission(self, request, obj=None):
        # A finalized brief is a locked snapshot of what leadership read (FR-30.4).
        if obj is not None and obj.is_locked:
            return False
        return super().has_change_permission(request, obj)


admin.site.register(DailyBriefIssue)
