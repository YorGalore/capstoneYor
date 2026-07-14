from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("ringkasan/", views.ringkasan, name="ringkasan"),
    path("umpan/", views.feed, name="feed"),
    path("umpan/<int:mention_id>/koreksi-sentimen/", views.correct_sentiment, name="correct_sentiment"),
    path("war-room/", views.war_room, name="war_room"),
    path("narasi/", views.narasi, name="narasi"),
    path("regional/", views.regional, name="regional"),
    path("ekspor/mention/", views.export_mentions, name="export_mentions"),
    path("taksonomi/", views.taxonomy_view, name="taxonomy"),
    path("taksonomi/<int:mention_id>/label/", views.assign_issue, name="assign_issue"),
    path("taksonomi/gabung/", views.merge_issues, name="merge_issues"),
    path("taksonomi/gabung/<int:history_id>/batal/", views.unmerge_issues, name="unmerge_issues"),
]
