from django.urls import path

from . import views

app_name = "coordination"

urlpatterns = [
    path("koordinasi/", views.koordinasi, name="koordinasi"),
    path("koordinasi/<str:cluster_code>/eskalasi/", views.escalate_cluster, name="escalate_cluster"),
    path("koordinasi/<str:cluster_code>/tandai-organik/", views.mark_cluster_organic, name="mark_cluster_organic"),
]
