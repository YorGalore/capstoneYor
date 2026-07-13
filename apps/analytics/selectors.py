from collections import OrderedDict

from django.db.models import Count, Sum
from django.utils import timezone

from .models import Alert, Coalition, Mention

SENTIMENT_LABELS = OrderedDict([
    (Mention.SENTIMENT_POSITIVE, "Positif"),
    (Mention.SENTIMENT_NEUTRAL, "Netral"),
    (Mention.SENTIMENT_NEGATIVE, "Negatif"),
])

EMOTION_LABELS = dict(Mention.EMOTION_CHOICES)


def ringkasan_summary(project, days=30):
    since = timezone.now() - timezone.timedelta(days=days)
    qs = Mention.objects.filter(project=project, posted_at__gte=since, is_political=False)

    total_mentions = qs.count()
    total_interactions = qs.aggregate(total=Sum("engagement_count"))["total"] or 0
    unique_authors = qs.values("author_handle").distinct().count()

    sentiment_counts = {row["sentiment"]: row["n"] for row in qs.values("sentiment").annotate(n=Count("id"))}
    sentiment_breakdown = []
    for key, label in SENTIMENT_LABELS.items():
        count = sentiment_counts.get(key, 0)
        pct = round((count / total_mentions) * 100) if total_mentions else 0
        sentiment_breakdown.append({"key": key, "label": label, "count": count, "pct": pct})

    source_breakdown = []
    for row in qs.values("platform__display_name").annotate(n=Count("id")).order_by("-n"):
        source_breakdown.append({
            "name": row["platform__display_name"],
            "count": row["n"],
            "pct": round((row["n"] / total_mentions) * 100) if total_mentions else 0,
        })

    emotion_counts = {row["emotion"]: row["n"] for row in qs.values("emotion").annotate(n=Count("id"))}
    emotion_breakdown = []
    for key, label in EMOTION_LABELS.items():
        count = emotion_counts.get(key, 0)
        pct = round((count / total_mentions) * 100) if total_mentions else 0
        emotion_breakdown.append({"key": key, "label": label, "count": count, "pct": pct})
    emotion_breakdown.sort(key=lambda item: item["count"], reverse=True)

    timeline = _daily_timeline(qs, since, days)
    positive_pct = next(
        (s["pct"] for s in sentiment_breakdown if s["key"] == Mention.SENTIMENT_POSITIVE), 0
    )
    health_index = round((positive_pct * 0.7) + (min(total_mentions, 5000) / 5000 * 30))

    return {
        "total_mentions": total_mentions,
        "total_interactions": total_interactions,
        "unique_authors": unique_authors,
        "sentiment_breakdown": sentiment_breakdown,
        "source_breakdown": source_breakdown,
        "emotion_breakdown": emotion_breakdown,
        "timeline_chart": timeline_chart(timeline),
        "health_index": health_index,
        "positive_pct": positive_pct,
    }


def _daily_timeline(qs, since, days):
    buckets = OrderedDict()
    for offset in range(days):
        day = (since + timezone.timedelta(days=offset)).date()
        buckets[day] = {"positive": 0, "neutral": 0, "negative": 0}

    for mention in qs.only("posted_at", "sentiment"):
        day = mention.posted_at.date()
        if day in buckets:
            buckets[day][mention.sentiment] += 1

    return list(buckets.values())


def _scale_points(values, width, height, max_value):
    if not values:
        return ""
    step = width / max(len(values) - 1, 1)
    points = []
    for index, value in enumerate(values):
        x = round(index * step, 1)
        y = round(height - (value / max_value * height), 1) if max_value else height
        points.append(f"{x},{y}")
    return " ".join(points)


def timeline_chart(timeline, width=760, height=230):
    max_value = max(
        [max(day["positive"], day["neutral"], day["negative"]) for day in timeline] or [0]
    ) or 1
    return {
        "positive_points": _scale_points([d["positive"] for d in timeline], width, height, max_value),
        "neutral_points": _scale_points([d["neutral"] for d in timeline], width, height, max_value),
        "negative_points": _scale_points([d["negative"] for d in timeline], width, height, max_value),
        "width": width,
        "height": height,
    }


def recent_alerts(limit=5):
    return list(Alert.objects.select_related("rule").order_by("-triggered_at")[:limit])


def war_room_summary(issue):
    now = timezone.now()
    last_hour = Mention.objects.filter(issue=issue, posted_at__gte=now - timezone.timedelta(hours=1))
    prev_window = Mention.objects.filter(
        issue=issue,
        posted_at__gte=now - timezone.timedelta(hours=4),
        posted_at__lt=now - timezone.timedelta(hours=1),
    )

    mentions_last_hour = last_hour.count()
    negative_last_hour = last_hour.filter(sentiment=Mention.SENTIMENT_NEGATIVE).count()
    negative_ratio = round((negative_last_hour / mentions_last_hour) * 100) if mentions_last_hour else 0

    prev_hourly_avg = (prev_window.count() / 3) or 1
    hourly_change_pct = round(((mentions_last_hour - prev_hourly_avg) / prev_hourly_avg) * 100)

    cumulative_reach = Mention.objects.filter(issue=issue).aggregate(total=Sum("reach_estimate"))["total"] or 0

    from apps.coordination.models import ClusterAccount, CoordinationCluster
    coordinated_cluster_count = CoordinationCluster.objects.filter(
        issue=issue, status=CoordinationCluster.STATUS_FLAGGED
    ).count()
    top_spreaders = list(
        ClusterAccount.objects.filter(cluster__issue=issue)
        .select_related("cluster")
        .order_by("-reach")[:5]
    )

    timeline = _hourly_timeline(issue, now)
    hotspots = _geo_hotspots(issue)

    return {
        "issue": issue,
        "mentions_last_hour": mentions_last_hour,
        "negative_ratio": negative_ratio,
        "hourly_change_pct": hourly_change_pct,
        "cumulative_reach": cumulative_reach,
        "coordinated_cluster_count": coordinated_cluster_count,
        "timeline_chart": timeline_chart(timeline, width=800, height=210),
        "top_spreaders": top_spreaders,
        "hotspots": hotspots,
    }


def _hourly_timeline(issue, now, hours=12, bucket_minutes=5):
    since = now - timezone.timedelta(hours=hours)
    bucket_count = hours * 60 // bucket_minutes
    buckets = [{"positive": 0, "neutral": 0, "negative": 0} for _ in range(bucket_count)]
    for mention in Mention.objects.filter(issue=issue, posted_at__gte=since).only("posted_at", "sentiment"):
        elapsed_minutes = (mention.posted_at - since).total_seconds() / 60
        index = min(int(elapsed_minutes // bucket_minutes), bucket_count - 1)
        buckets[index][mention.sentiment] += 1
    return buckets


def _geo_hotspots(issue, limit=6):
    rows = (
        Mention.objects.filter(issue=issue, province__isnull=False)
        .values("province__name")
        .annotate(n=Count("id"))
        .order_by("-n")[:limit]
    )
    rows = list(rows)
    max_count = rows[0]["n"] if rows else 1
    return [
        {"name": row["province__name"], "count": row["n"], "pct": round((row["n"] / max_count) * 100)}
        for row in rows
    ]


def narasi_summary(issue):
    coalitions = Coalition.objects.all()
    total_political = Mention.objects.filter(issue=issue, is_political=True).count()
    total_attributed = Mention.objects.filter(issue=issue, coalition__isnull=False).count()
    unattributed_pct = (
        round(((total_political - total_attributed) / total_political) * 100)
        if total_political else 0
    )

    coalition_data = []
    for coalition in coalitions:
        qs = Mention.objects.filter(issue=issue, coalition=coalition)
        count = qs.count()
        share_pct = round((count / total_attributed) * 100) if total_attributed else 0
        sentiment_counts = {row["sentiment"]: row["n"] for row in qs.values("sentiment").annotate(n=Count("id"))}
        sentiment_breakdown = []
        for key, label in SENTIMENT_LABELS.items():
            c = sentiment_counts.get(key, 0)
            pct = round((c / count) * 100) if count else 0
            sentiment_breakdown.append({"key": key, "label": label, "pct": pct})
        coalition_data.append({
            "coalition": coalition,
            "count": count,
            "share_pct": share_pct,
            "sentiment_breakdown": sentiment_breakdown,
            "trend_chart": _coalition_trend(qs),
        })

    return {
        "issue": issue,
        "total_attributed": total_attributed,
        "unattributed_pct": unattributed_pct,
        "coalitions": coalition_data,
        "overlay_chart": _overlay_trend(coalitions, issue),
    }


def _coalition_trend(qs, days=30, width=560, height=90):
    since = timezone.now() - timezone.timedelta(days=days)
    daily = [0] * days
    for mention in qs.filter(posted_at__gte=since).only("posted_at"):
        offset = (mention.posted_at - since).days
        if 0 <= offset < days:
            daily[offset] += 1
    max_value = max(daily) or 1
    return {"points": _scale_points(daily, width, height, max_value), "width": width, "height": height}


def _overlay_trend(coalitions, issue, days=30, width=1160, height=150):
    since = timezone.now() - timezone.timedelta(days=days)
    series = {}
    for coalition in coalitions:
        daily = [0] * days
        for mention in Mention.objects.filter(
            issue=issue, coalition=coalition, posted_at__gte=since
        ).only("posted_at"):
            offset = (mention.posted_at - since).days
            if 0 <= offset < days:
                daily[offset] += 1
        max_value = max(daily) or 1
        series[coalition.slug] = _scale_points(daily, width, height, max_value)
    return {"series": series, "width": width, "height": height}
