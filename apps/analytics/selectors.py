import math
from collections import OrderedDict

from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.core.models import Province

from .models import Alert, Author, Coalition, DailyBrief, Mention

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

    # A raw count means nothing without a reference point, so every headline number
    # is paired with the same window immediately before it (trend) and a derived
    # figure that says what the count implies (rate, intensity, concentration).
    prev_since = since - timezone.timedelta(days=days)
    prev_qs = Mention.objects.filter(
        project=project, posted_at__gte=prev_since, posted_at__lt=since, is_political=False
    )
    prev_mentions = prev_qs.count()
    prev_interactions = prev_qs.aggregate(total=Sum("engagement_count"))["total"] or 0
    prev_authors = prev_qs.values("author_handle").distinct().count()

    per_day = round(total_mentions / days, 1)
    interactions_per_mention = round(total_interactions / total_mentions) if total_mentions else 0
    mentions_per_author = round(total_mentions / unique_authors, 1) if unique_authors else 0

    metrics = {
        "mentions": {
            "value": total_mentions,
            "delta": _pct_delta(total_mentions, prev_mentions),
            "context": f"± {per_day} per hari",
        },
        "interactions": {
            "value": total_interactions,
            "delta": _pct_delta(total_interactions, prev_interactions),
            "context": f"± {interactions_per_mention} per sebutan",
        },
        "authors": {
            "value": unique_authors,
            "delta": _pct_delta(unique_authors, prev_authors),
            "context": f"± {mentions_per_author} sebutan/penulis",
        },
    }

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

    dates = [(since + timezone.timedelta(days=offset)).date() for offset in range(days)]
    timeline = _daily_timeline(qs, since, days)
    positive_pct = next(
        (s["pct"] for s in sentiment_breakdown if s["key"] == Mention.SENTIMENT_POSITIVE), 0
    )
    negative_pct = next(
        (s["pct"] for s in sentiment_breakdown if s["key"] == Mention.SENTIMENT_NEGATIVE), 0
    )
    prev_negative = prev_qs.filter(sentiment=Mention.SENTIMENT_NEGATIVE).count()
    prev_negative_pct = round((prev_negative / prev_mentions) * 100) if prev_mentions else 0
    negative_shift = negative_pct - prev_negative_pct  # percentage points, +/-

    health_index = round((positive_pct * 0.7) + (min(total_mentions, 5000) / 5000 * 30))
    if health_index >= 70:
        health_band = "Sehat"
    elif health_index >= 45:
        health_band = "Waspada"
    else:
        health_band = "Perlu perhatian"

    # The aggregates say how much and how positive; these say about what and by whom —
    # the actual issues driving volume and the individual posts carrying the reach.
    top_issues = _top_issues(qs, total_mentions)
    top_mentions = list(qs.select_related("platform").order_by("-engagement_count")[:3])

    insight = _ringkasan_insight(
        timeline=timeline,
        total_mentions=total_mentions,
        positive_pct=positive_pct,
        negative_pct=negative_pct,
        emotion_breakdown=emotion_breakdown,
        source_breakdown=source_breakdown,
    )

    return {
        "total_mentions": total_mentions,
        "total_interactions": total_interactions,
        "unique_authors": unique_authors,
        "metrics": metrics,
        "sentiment_breakdown": sentiment_breakdown,
        "source_breakdown": source_breakdown,
        "emotion_breakdown": emotion_breakdown,
        "timeline_chart": timeline_chart(timeline, dates=dates),
        "health_index": health_index,
        "health_band": health_band,
        "positive_pct": positive_pct,
        "negative_pct": negative_pct,
        "negative_shift": negative_shift,
        "top_issues": top_issues,
        "top_mentions": top_mentions,
        "insight": insight,
    }


def _top_issues(qs, total_mentions, limit=4):
    """The taxonomy issues driving the window's volume, each with the share of its own
    mentions that are negative — so 'which issue' comes with 'and is it a problem'."""
    rows = (
        qs.filter(issue_label__isnull=False)
        .values("issue_label__issue__name")
        .annotate(
            n=Count("id"),
            negative=Count("id", filter=Q(sentiment=Mention.SENTIMENT_NEGATIVE)),
        )
        .order_by("-n")[:limit]
    )
    issues = []
    for row in rows:
        count = row["n"]
        issues.append({
            "name": row["issue_label__issue__name"],
            "count": count,
            "pct": round((count / total_mentions) * 100) if total_mentions else 0,
            "negative_pct": round((row["negative"] / count) * 100) if count else 0,
        })
    return issues


def _pct_delta(current, previous):
    """Percentage change vs the previous window, with a direction the template colours.
    Volume moving is information, not a verdict — direction is 'up'/'down'/'flat', not
    good/bad; the sentiment and health readings carry the value judgement."""
    if not previous:
        # No baseline to compare against: report the arrival of activity, not a
        # meaningless "+100%" off zero, and stay silent when there is nothing either side.
        return {"pct": None, "direction": "up" if current else "flat", "label": "baru" if current else "—"}
    change = round(((current - previous) / previous) * 100)
    direction = "up" if change > 0 else "down" if change < 0 else "flat"
    return {"pct": abs(change), "direction": direction, "label": f"{'+' if change > 0 else '−' if change < 0 else ''}{abs(change)}%"}


def _ringkasan_insight(*, timeline, total_mentions, positive_pct, negative_pct,
                       emotion_breakdown, source_breakdown):
    """Turn the raw numbers into a one-line read of the situation so the landing page
    leads with meaning, not just counts. Returns a headline, supporting detail, and a
    tone the template uses to colour the banner (positive / negative / neutral)."""
    # Volume momentum: last 7 days of the window vs the 7 before it.
    def _window_total(days_slice):
        return sum(d["positive"] + d["neutral"] + d["negative"] for d in days_slice)

    recent = _window_total(timeline[-7:])
    prior = _window_total(timeline[-14:-7])
    if prior:
        volume_change_pct = round(((recent - prior) / prior) * 100)
    else:
        volume_change_pct = 100 if recent else 0

    dominant_emotion = emotion_breakdown[0] if emotion_breakdown else None
    top_source = source_breakdown[0] if source_breakdown else None

    if total_mentions == 0:
        return {
            "tone": "neutral",
            "headline": "Belum ada sebutan pada periode ini",
            "detail": "Belum ada data untuk dianalisis. Pastikan kata kunci pemantauan aktif.",
            "volume_change_pct": 0,
        }

    if negative_pct >= 35 or (negative_pct >= 25 and volume_change_pct >= 25):
        tone = "negative"
        headline = f"Perhatian: {negative_pct}% sebutan bernada negatif"
    elif positive_pct >= 50 and volume_change_pct >= 0:
        tone = "positive"
        headline = f"Kondisi sehat: {positive_pct}% sebutan positif"
    else:
        tone = "neutral"
        headline = "Sentimen relatif seimbang, pantau perkembangan"

    detail_parts = []
    if recent == 0 and prior > 0:
        detail_parts.append("tidak ada sebutan dalam 7 hari terakhir")
    elif volume_change_pct > 5:
        detail_parts.append(f"volume sebutan naik {volume_change_pct}% dibanding minggu lalu")
    elif volume_change_pct < -5:
        detail_parts.append(f"volume sebutan turun {abs(volume_change_pct)}% dibanding minggu lalu")
    else:
        detail_parts.append("volume sebutan relatif stabil")
    if dominant_emotion and dominant_emotion["pct"]:
        detail_parts.append(f"emosi dominan {dominant_emotion['label'].lower()} ({dominant_emotion['pct']}%)")
    if top_source:
        detail_parts.append(f"terbanyak dari {top_source['name']}")

    return {
        "tone": tone,
        "headline": headline,
        "detail": ", ".join(detail_parts).capitalize() + ".",
        "volume_change_pct": volume_change_pct,
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


def timeline_chart(timeline, width=760, height=230, dates=None):
    max_value = max(
        [max(day["positive"], day["neutral"], day["negative"]) for day in timeline] or [0]
    ) or 1
    chart = {
        "positive_points": _scale_points([d["positive"] for d in timeline], width, height, max_value),
        "neutral_points": _scale_points([d["neutral"] for d in timeline], width, height, max_value),
        "negative_points": _scale_points([d["negative"] for d in timeline], width, height, max_value),
        "width": width,
        "height": height,
        "max_value": max_value,
        "mid_value": round(max_value / 2),
    }
    # Axis labels turn the polylines from a shape into something readable: a handful of
    # evenly spaced date ticks and a marker on the worst negative day. Only computed when
    # the caller has real calendar dates (the daily overview), not the hourly war room.
    if dates and len(dates) == len(timeline) and len(dates) > 1:
        n = len(dates)
        tick_indexes = sorted({0, n // 4, n // 2, (3 * n) // 4, n - 1})
        # Formatted as dot-strings, not floats: these land directly in a CSS `left:`
        # value, and under an id/ID locale Django would render a float as "24,1" —
        # invalid CSS that the browser silently drops, collapsing every label to 0.
        chart["x_labels"] = [
            {"label": f"{dates[i].day}/{dates[i].month}", "left_pct": f"{i / (n - 1) * 100:.1f}"}
            for i in tick_indexes
        ]
        peak_i = max(range(n), key=lambda i: timeline[i]["negative"])
        if timeline[peak_i]["negative"] > 0:
            chart["peak"] = {
                "date": dates[peak_i],
                "value": timeline[peak_i]["negative"],
                "left_pct": f"{peak_i / (n - 1) * 100:.1f}",
            }
    return chart


def recent_alerts(project, limit=5):
    return list(
        Alert.objects.filter(project=project)
        .select_related("rule")
        .order_by("-triggered_at")[:limit]
    )


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
            "dominant_themes": _dominant_themes(qs),
            "trend_chart": _coalition_trend(qs),
        })

    return {
        "issue": issue,
        "total_attributed": total_attributed,
        "unattributed_pct": unattributed_pct,
        "coalitions": coalition_data,
        "overlay_chart": _overlay_trend(coalitions, issue),
    }


def _dominant_themes(qs, limit=4):
    total = qs.exclude(theme="").count()
    if not total:
        return []
    rows = (
        qs.exclude(theme="")
        .values("theme")
        .annotate(n=Count("id"))
        .order_by("-n")[:limit]
    )
    return [{"theme": row["theme"], "pct": round((row["n"] / total) * 100)} for row in rows]


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


_ID_MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def _id_date_label(d):
    return f"{d.day} {_ID_MONTHS[d.month - 1]}"


def _heat_intensity_band(intensity):
    # Bucket a 0..1 intensity value into 5 discrete bands for CSS-class-based shading,
    # mirroring the small number of distinct tile shades in the design mockup.
    band = min(4, int(intensity * 5))
    return band + 1


def _province_trend(qs, days=30, width=360, height=90):
    since = timezone.now() - timezone.timedelta(days=days)
    daily = [0] * days
    for mention in qs.filter(posted_at__gte=since).only("posted_at"):
        offset = (mention.posted_at - since).days
        if 0 <= offset < days:
            daily[offset] += 1
    max_value = max(daily) or 1
    points = _scale_points(daily, width, height, max_value)
    area_path = ""
    if points:
        area_path = "M" + " L".join(points.split(" ")) + f" L{width},{height} L0,{height} Z"

    start_date = since.date()
    mid_date = (since + timezone.timedelta(days=days // 2)).date()
    end_date = (since + timezone.timedelta(days=days - 1)).date()
    return {
        "points": points,
        "area_path": area_path,
        "width": width,
        "height": height,
        "labels": [_id_date_label(start_date), _id_date_label(mid_date), _id_date_label(end_date)],
    }


def regional_summary(project, selected_province=None):
    rows = (
        Mention.objects.filter(project=project, is_political=False, province__isnull=False)
        .values("province__name")
        .annotate(
            n=Count("id"),
            positive=Count("id", filter=Q(sentiment=Mention.SENTIMENT_POSITIVE)),
            neutral=Count("id", filter=Q(sentiment=Mention.SENTIMENT_NEUTRAL)),
            negative=Count("id", filter=Q(sentiment=Mention.SENTIMENT_NEGATIVE)),
        )
        .order_by("-n")
    )
    province_rows = []
    for row in rows:
        total = row["n"] or 1
        negative_pct = round((row["negative"] / total) * 100)
        province_rows.append({
            "name": row["province__name"],
            "count": row["n"],
            "positive_pct": round((row["positive"] / total) * 100),
            "neutral_pct": round((row["neutral"] / total) * 100),
            "negative_pct": negative_pct,
            "flagged": negative_pct > 50,
        })

    max_count = max((r["count"] for r in province_rows), default=0) or 1
    heat_tiles = [
        {
            "name": r["name"],
            "count": r["count"],
            "intensity": round(r["count"] / max_count, 3),
            "intensity_band": _heat_intensity_band(r["count"] / max_count),
            "flagged": r["flagged"],
        }
        for r in province_rows
    ]

    selected = None
    if province_rows:
        target_name = selected_province or max(province_rows, key=lambda r: r["negative_pct"])["name"]
        selected_row = next((r for r in province_rows if r["name"] == target_name), province_rows[0])
        province = Province.objects.filter(name=selected_row["name"]).first()
        regency_rows = (
            Mention.objects.filter(project=project, province=province, regency__isnull=False)
            .values("regency__name")
            .annotate(n=Count("id"))
            .order_by("-n")[:6]
        )
        regency_rows = list(regency_rows)
        max_regency = regency_rows[0]["n"] if regency_rows else 1
        province_qs = Mention.objects.filter(project=project, province=province)
        selected = {
            **selected_row,
            "regencies": [
                {"name": r["regency__name"], "count": r["n"], "pct": round((r["n"] / max_regency) * 100)}
                for r in regency_rows
            ],
            "dominant_themes": _dominant_themes(province_qs),
            "trend_chart": _province_trend(province_qs),
        }

    return {"province_rows": province_rows[:10], "heat_tiles": heat_tiles, "selected": selected}


def sosiograf_summary(project, days=30, max_nodes=20, width=760, height=560):
    """Interaction sociograph (Sosiograf): the most influential authors of the
    last ``days`` days as graph nodes, linked when they push the same theme.
    Accounts that belong to a flagged coordination cluster are marked so the
    analyst can see amplification structure at a glance.

    The layout is computed server-side (deterministic circular layout grouped
    by theme) so the page needs no JS graph library.
    """
    since = timezone.now() - timezone.timedelta(days=days)
    qs = Mention.objects.filter(project=project, posted_at__gte=since)

    author_rows = list(
        qs.exclude(author_handle="")
        .values("author_handle", "platform__slug", "platform__display_name")
        .annotate(
            n=Count("id"),
            reach=Sum("reach_estimate"),
            engagement=Sum("engagement_count"),
            negative=Count("id", filter=Q(sentiment=Mention.SENTIMENT_NEGATIVE)),
            positive=Count("id", filter=Q(sentiment=Mention.SENTIMENT_POSITIVE)),
        )
        .order_by("-reach", "-n")[:max_nodes]
    )
    if not author_rows:
        return None

    handles = [row["author_handle"] for row in author_rows]

    # Dominant theme per author — the edge criterion.
    theme_by_author = {}
    theme_rows = (
        qs.filter(author_handle__in=handles)
        .exclude(theme="")
        .values("author_handle", "theme")
        .annotate(n=Count("id"))
        .order_by("author_handle", "-n")
    )
    for row in theme_rows:
        theme_by_author.setdefault(row["author_handle"], row["theme"])

    # Accounts sitting inside a flagged coordination cluster.
    from apps.coordination.models import ClusterAccount, CoordinationCluster

    coordinated = set(
        ClusterAccount.objects.filter(
            cluster__issue__project=project,
            cluster__status=CoordinationCluster.STATUS_FLAGGED,
            handle__in=handles,
        ).values_list("handle", flat=True)
    )

    # Normalized influence scores where the enrichment job has produced them
    # (FR-3.3); reach is the fallback for handles not yet linked to an Author.
    influence_by_handle = {
        (handle, slug): float(score)
        for handle, slug, score in Author.objects.filter(
            handle__in=handles, influence_score__gt=0
        ).values_list("handle", "platform__slug", "influence_score")
    }

    def _weight(row):
        return influence_by_handle.get(
            (row["author_handle"], row["platform__slug"])
        ) or float(row["reach"] or 0)

    # Group nodes by theme so linked nodes sit next to each other on the circle.
    author_rows.sort(key=lambda r: (theme_by_author.get(r["author_handle"], "~"), -_weight(r)))

    max_weight = max(_weight(row) for row in author_rows) or 1
    cx, cy = width / 2, height / 2
    ring = min(width, height) / 2 - 70
    nodes = []
    for index, row in enumerate(author_rows):
        angle = (2 * math.pi * index) / len(author_rows) - math.pi / 2
        total = row["n"] or 1
        negative_pct = round((row["negative"] / total) * 100)
        if negative_pct >= 50:
            sentiment = "negative"
        elif round((row["positive"] / total) * 100) >= 50:
            sentiment = "positive"
        else:
            sentiment = "neutral"
        nodes.append({
            "handle": row["author_handle"],
            "platform": row["platform__display_name"],
            "influence": influence_by_handle.get((row["author_handle"], row["platform__slug"]), 0),
            "x": round(cx + ring * math.cos(angle), 1),
            "y": round(cy + ring * math.sin(angle), 1),
            "radius": round(9 + (_weight(row) / max_weight) * 21, 1),
            "mentions": row["n"],
            "reach": row["reach"] or 0,
            "engagement": row["engagement"] or 0,
            "negative_pct": negative_pct,
            "sentiment": sentiment,
            "theme": theme_by_author.get(row["author_handle"], ""),
            "coordinated": row["author_handle"] in coordinated,
        })

    edges = []
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            if a["theme"] and a["theme"] == b["theme"]:
                edges.append({
                    "x1": a["x"], "y1": a["y"], "x2": b["x"], "y2": b["y"],
                    "coordinated": a["coordinated"] and b["coordinated"],
                })

    theme_counts = {}
    for node in nodes:
        if node["theme"]:
            theme_counts[node["theme"]] = theme_counts.get(node["theme"], 0) + 1
    theme_groups = sorted(theme_counts.items(), key=lambda kv: -kv[1])

    influencers = sorted(nodes, key=lambda n: -(n["influence"] or n["reach"]))[:8]
    return {
        "width": width,
        "height": height,
        "nodes": nodes,
        "edges": edges,
        "influencers": influencers,
        "coordinated_count": sum(1 for n in nodes if n["coordinated"]),
        "theme_groups": [
            {"theme": theme, "count": count} for theme, count in theme_groups[:6]
        ],
        "node_count": len(nodes),
        "edge_count": len(edges),
        "days": days,
    }


def laporan_summary(project, days=30):
    """Report center (Laporan): finalized daily briefs as the archive of record,
    plus a rolling recap of the reporting period for the periodic report."""
    since = timezone.now() - timezone.timedelta(days=days)
    qs = Mention.objects.filter(project=project, posted_at__gte=since)

    total_mentions = qs.count()
    sentiment_counts = {
        row["sentiment"]: row["n"] for row in qs.values("sentiment").annotate(n=Count("id"))
    }
    sentiment_breakdown = []
    for key, label in SENTIMENT_LABELS.items():
        count = sentiment_counts.get(key, 0)
        pct = round((count / total_mentions) * 100) if total_mentions else 0
        sentiment_breakdown.append({"key": key, "label": label, "count": count, "pct": pct})

    platform_rows = []
    for row in qs.values("platform__display_name").annotate(n=Count("id")).order_by("-n"):
        platform_rows.append({
            "name": row["platform__display_name"],
            "count": row["n"],
            "pct": round((row["n"] / total_mentions) * 100) if total_mentions else 0,
        })

    top_themes = _dominant_themes(qs, limit=6)
    timeline = _daily_timeline(qs, since, days)

    briefs = list(DailyBrief.objects.filter(project=project).order_by("-brief_date")[:30])
    final_count = sum(1 for b in briefs if b.status == DailyBrief.STATUS_FINAL)

    return {
        "days": days,
        "period_start": since.date(),
        "period_end": timezone.now().date(),
        "total_mentions": total_mentions,
        "total_reach": qs.aggregate(total=Sum("reach_estimate"))["total"] or 0,
        "unique_authors": qs.values("author_handle").distinct().count(),
        "sentiment_breakdown": sentiment_breakdown,
        "platform_rows": platform_rows,
        "top_themes": top_themes,
        "timeline_chart": timeline_chart(timeline, width=1160, height=180),
        "briefs": briefs,
        "final_count": final_count,
        "draft_count": len(briefs) - final_count,
    }


def incident_board(request, window="7", opd_slug="", severity=""):
    """Incidents for the board, split into operator candidates and confirmed items.

    Both halves come from the same tenant-scoped queryset: candidates are shown
    alongside confirmed incidents rather than hidden in a separate queue, so the
    operator's review work stays visible in context.

    The time window only ever hides *terminal* incidents (resolved/closed) older
    than the window: an incident that is still open or in progress must never
    disappear from the board just because it is old, since that is precisely the
    unresolved work the board exists to surface. Passing ``window="0"`` disables
    the window filter entirely (no incident is hidden by age).
    """
    from datetime import timedelta

    from django.utils import timezone

    from apps.core.selectors import scope_to_tenant

    from .models import Incident, OPD

    queryset = scope_to_tenant(
        Incident.objects.select_related("assigned_opd", "regency"), request
    )
    # Same tenant gate as the incidents themselves, so the OPD filter can never
    # offer another tenant's units.
    opds = scope_to_tenant(OPD.objects.filter(is_active=True), request)

    try:
        days = int(window)
    except (TypeError, ValueError):
        days = 7
    if days > 0:
        cutoff = timezone.now() - timedelta(days=days)
        terminal_statuses = [Incident.STATUS_RESOLVED, Incident.STATUS_CLOSED]
        queryset = queryset.filter(
            Q(status__in=terminal_statuses, created_at__gte=cutoff)
            | ~Q(status__in=terminal_statuses)
        )

    if opd_slug:
        queryset = queryset.filter(assigned_opd__slug=opd_slug)
    if severity:
        queryset = queryset.filter(severity=severity)

    confirmed = list(queryset.filter(is_confirmed=True))
    candidates = list(queryset.filter(is_confirmed=False))

    return {
        "confirmed": confirmed,
        "candidates": candidates,
        "opds": opds,
        "counts": {
            "confirmed": len(confirmed),
            "candidates": len(candidates),
            # Severity is situational, not a workflow state: a critical candidate
            # is the most urgent thing on the board (nobody has even confirmed it),
            # so "Kritis" counts across candidates and confirmed alike.
            "critical": sum(
                1 for i in confirmed + candidates if i.severity == Incident.SEVERITY_CRITICAL
            ),
            "open": sum(1 for i in confirmed if i.is_open),
        },
    }


def incident_detail(request, incident_id):
    """One incident with its timeline and related mentions, tenant-scoped."""
    from apps.core.selectors import scope_to_tenant

    from .models import Incident

    return (
        scope_to_tenant(
            Incident.objects.select_related("assigned_opd", "regency", "issue"), request
        )
        .prefetch_related("events", "mentions__platform")
        .filter(pk=incident_id)
        .first()
    )
