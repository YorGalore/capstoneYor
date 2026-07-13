from django.contrib import admin

from .models import ClusterAccount, CoordinationCluster, CoordinationSignal, DuplicateTextSample


class ClusterAccountInline(admin.TabularInline):
    model = ClusterAccount
    extra = 0


class CoordinationSignalInline(admin.TabularInline):
    model = CoordinationSignal
    extra = 0


class DuplicateTextSampleInline(admin.TabularInline):
    model = DuplicateTextSample
    extra = 0


@admin.register(CoordinationCluster)
class CoordinationClusterAdmin(admin.ModelAdmin):
    list_display = ("cluster_code", "score", "status", "account_count")
    inlines = [ClusterAccountInline, CoordinationSignalInline, DuplicateTextSampleInline]
