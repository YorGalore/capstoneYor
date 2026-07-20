from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("ringkasan/", views.ringkasan, name="ringkasan"),
    path("umpan/", views.feed, name="feed"),
    path("umpan/<int:mention_id>/koreksi-sentimen/", views.correct_sentiment, name="correct_sentiment"),
    path("war-room/", views.war_room, name="war_room"),
    path("war-room/<int:issue_id>/aksi/", views.log_response, name="log_response"),
    path("narasi/", views.narasi, name="narasi"),
    path("regional/", views.regional, name="regional"),
    path("sosiograf/", views.sosiograf, name="sosiograf"),
    path("laporan/", views.laporan, name="laporan"),
    path("ekspor/mention/", views.export_mentions, name="export_mentions"),
    path("brief/", views.brief_view, name="brief"),
    path("brief/buat/", views.generate_brief, name="generate_brief"),
    path("brief/<int:brief_id>/cetak/", views.brief_print, name="brief_print"),
    path("brief/isu/<int:issue_id>/tinjau/", views.review_brief_issue, name="review_brief_issue"),
    path("brief/<int:brief_id>/finalisasi/", views.finalize_brief, name="finalize_brief"),
    path("taksonomi/", views.taxonomy_view, name="taxonomy"),
    path("taksonomi/<int:mention_id>/label/", views.assign_issue, name="assign_issue"),
    path("taksonomi/gabung/", views.merge_issues, name="merge_issues"),
    path("taksonomi/gabung/<int:history_id>/batal/", views.unmerge_issues, name="unmerge_issues"),
]
