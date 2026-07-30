import math
from collections import OrderedDict
from urllib.parse import urlsplit

from django.db.models import Avg, Count, Max, Min, Q, Sum
from django.utils import timezone

from apps.core.models import Platform, Province

from .metrics import EvidenceRef, Metric, confidence_stats, own_government_q
from .models import (
    ActorSentimentAssessment, Alert, Author, Camp, DailyBrief, DriverCandidate,
    GovernmentProgram, Issue, Mention, MentionAttribution, MentionDriver,
    PoliticalActor, ThreadInsight,
)

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


def attribution_summary(project, days=30, sentiment=Mention.SENTIMENT_NEGATIVE):
    """Who the sentiment in a window is actually directed at.

    Answers the question a bare "60% negatif" cannot: how much of that negativity
    is about *us*. Computed over attribution rows rather than mentions, because a
    post blaming both the central and the regency government genuinely belongs to
    both — so the shares here and the mention counts elsewhere use different
    denominators, and every returned Metric says so in its ``method``.
    """
    since = timezone.now() - timezone.timedelta(days=days)
    rows = MentionAttribution.objects.filter(
        mention__project=project,
        mention__posted_at__gte=since,
        mention__is_political=False,
        sentiment=sentiment,
    ).select_related("target", "target__parent")

    total = rows.count()
    if not total:
        return {
            "total": 0,
            "levels": [],
            "own_government": Metric(
                value=0, unit="percent",
                label="ditujukan ke pemerintah daerah ini",
                method="tidak ada atribusi pada periode ini",
                evidence=EvidenceRef("attribution", {"own_government": "1", "sentiment": sentiment}),
            ),
            "sentiment": sentiment,
        }

    # Roll every attribution up to its display level: an entity target reports
    # under its own level, and the tenant's OPD children also aggregate into the
    # "is this us?" number via own_government_q.
    by_level = OrderedDict()
    for row in rows:
        target = row.target
        bucket = by_level.setdefault(
            target.level,
            {
                "level": target.level,
                "label": target.get_level_display(),
                "rank": target.level_rank,
                "count": 0,
                "confidences": [],
                "entities": {},
            },
        )
        bucket["count"] += 1
        bucket["confidences"].append(row.confidence)
        entity = bucket["entities"].setdefault(
            target.id,
            {"id": target.id, "name": target.name, "count": 0, "confidences": []},
        )
        entity["count"] += 1
        entity["confidences"].append(row.confidence)

    levels = []
    for bucket in sorted(by_level.values(), key=lambda b: b["rank"]):
        confidence, low_pct = confidence_stats(bucket["confidences"])
        entities = []
        for entity in sorted(bucket["entities"].values(), key=lambda e: -e["count"]):
            e_conf, e_low = confidence_stats(entity["confidences"])
            entities.append({
                "name": entity["name"],
                "metric": Metric(
                    value=round((entity["count"] / bucket["count"]) * 100),
                    unit="percent",
                    label=f"{entity['name']} (dari {bucket['label'].lower()})",
                    method=(
                        f"atribusi {SENTIMENT_LABELS[sentiment].lower()} ke "
                        f"{entity['name']} ÷ atribusi {SENTIMENT_LABELS[sentiment].lower()} "
                        f"ke {bucket['label'].lower()}"
                    ),
                    evidence=EvidenceRef(
                        "attribution", {"target": entity["id"], "sentiment": sentiment}
                    ),
                    contributing=entity["count"],
                    confidence=e_conf,
                    low_confidence_pct=e_low,
                ),
            })
        levels.append({
            "level": bucket["level"],
            "label": bucket["label"],
            "metric": Metric(
                value=round((bucket["count"] / total) * 100),
                unit="percent",
                label=bucket["label"],
                method=(
                    f"atribusi {SENTIMENT_LABELS[sentiment].lower()} ke "
                    f"{bucket['label'].lower()} ÷ seluruh atribusi "
                    f"{SENTIMENT_LABELS[sentiment].lower()} ({total} baris atribusi, "
                    "satu sebutan dapat menyasar lebih dari satu pihak)"
                ),
                evidence=EvidenceRef(
                    "attribution", {"level": bucket["level"], "sentiment": sentiment}
                ),
                contributing=bucket["count"],
                confidence=confidence,
                low_confidence_pct=low_pct,
            ),
            "entities": entities,
        })

    own_rows = rows.filter(own_government_q(prefix="")).distinct()
    own_count = own_rows.count()
    own_conf, own_low = confidence_stats(
        list(own_rows.values_list("confidence", flat=True))
    )
    own_metric = Metric(
        value=round((own_count / total) * 100),
        unit="percent",
        label="ditujukan ke pemerintah daerah ini",
        method=(
            f"atribusi {SENTIMENT_LABELS[sentiment].lower()} ke pemerintah daerah ini "
            f"dan instansi di bawahnya ÷ seluruh atribusi "
            f"{SENTIMENT_LABELS[sentiment].lower()} ({total} baris atribusi)"
        ),
        evidence=EvidenceRef(
            "attribution", {"own_government": "1", "sentiment": sentiment}
        ),
        contributing=own_count,
        confidence=own_conf,
        low_confidence_pct=own_low,
    )

    return {
        "total": total,
        "levels": levels,
        "own_government": own_metric,
        "sentiment": sentiment,
    }


def driver_summary(project, days=30, limit=8):
    """Why the negative sentiment exists, ranked, each drillable to its evidence.

    Shares are over *labelled negative mentions*, not all mentions: the question
    is "of the complaints we have, what are they about", and mixing in unlabelled
    or non-negative content would answer a different one.
    """
    since = timezone.now() - timezone.timedelta(days=days)
    negative = Mention.objects.filter(
        project=project, posted_at__gte=since, is_political=False,
        sentiment=Mention.SENTIMENT_NEGATIVE,
    )
    total_negative = negative.count()
    labelled = negative.filter(drivers__isnull=False).distinct().count()

    rows = (
        MentionDriver.objects.filter(
            mention__project=project,
            mention__posted_at__gte=since,
            mention__is_political=False,
        )
        .values("driver_id", "driver__name", "driver__color")
        .annotate(n=Count("mention_id", distinct=True))
        .order_by("-n")[:limit]
    )

    drivers_out = []
    for row in rows:
        confidences = list(
            MentionDriver.objects.filter(
                driver_id=row["driver_id"],
                mention__project=project,
                mention__posted_at__gte=since,
            ).values_list("confidence", flat=True)
        )
        confidence, low_pct = confidence_stats(confidences)
        drivers_out.append({
            "name": row["driver__name"],
            "color": row["driver__color"],
            "metric": Metric(
                value=round((row["n"] / labelled) * 100) if labelled else 0,
                unit="percent",
                label=f"keluhan tentang {row['driver__name'].lower()}",
                method=(
                    f"sebutan negatif berlabel \"{row['driver__name']}\" ÷ seluruh "
                    f"sebutan negatif yang sudah berlabel alasan ({labelled} sebutan)"
                ),
                evidence=EvidenceRef("driver", {"driver": row["driver_id"]}),
                contributing=row["n"],
                confidence=confidence,
                low_confidence_pct=low_pct,
            ),
        })

    coverage = round((labelled / total_negative) * 100) if total_negative else 0
    return {
        "drivers": drivers_out,
        "total_negative": total_negative,
        "labelled": labelled,
        # Stated plainly rather than hidden: a reason breakdown covering 40% of
        # complaints is a different claim from one covering 95%.
        "coverage_pct": coverage,
        "pending_candidates": DriverCandidate.objects.filter(
            project=project, promoted_to__isnull=True, dismissed=False,
        ).count(),
    }


def thread_summary(project, days=30, limit=6):
    """Threads where the comment section diverges most from the post.

    Sorted by divergence rather than volume: a busy thread that agrees with its
    post needs no attention, and a quiet one that has turned does.
    """
    since = timezone.now() - timezone.timedelta(days=days)
    insights = list(
        ThreadInsight.objects.filter(
            root_mention__project=project, root_mention__posted_at__gte=since
        )
        .select_related("root_mention", "root_mention__platform")
        .order_by("-divergence_pp")[:limit]
    )

    threads = []
    for insight in insights:
        threads.append({
            "insight": insight,
            "root": insight.root_mention,
            "divergence": Metric(
                value=insight.divergence_pp,
                unit="points",
                label="selisih negativitas komentar terhadap posting",
                method=(
                    f"negativitas komentar ({insight.comment_negative_pct}%) − "
                    f"negativitas posting induk, dari {insight.comment_count} komentar"
                ),
                evidence=EvidenceRef("thread", {"root": insight.root_mention_id}),
                contributing=insight.comment_count,
                # Divergence is counted from stored sentiment labels rather than
                # inferred fresh, so its reliability is the comment coverage of
                # the intelligence stage, not a model score.
                confidence=(
                    round(insight.analysed_comment_count / insight.comment_count, 3)
                    if insight.comment_count else 0.0
                ),
            ),
            "shift": Metric(
                value=insight.opinion_shift_pp,
                unit="points",
                label="pergeseran opini dalam diskusi",
                method=(
                    "negativitas paruh akhir − paruh awal komentar, "
                    "diurutkan berdasarkan waktu"
                ),
                evidence=EvidenceRef("thread", {"root": insight.root_mention_id}),
                contributing=insight.comment_count,
                confidence=(
                    round(insight.analysed_comment_count / insight.comment_count, 3)
                    if insight.comment_count else 0.0
                ),
            ),
        })

    analysed = ThreadInsight.objects.filter(
        root_mention__project=project, root_mention__posted_at__gte=since
    )
    return {
        "threads": threads,
        "thread_count": analysed.count(),
        "diverging_count": analysed.filter(divergence_pp__gte=25).count(),
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
    """Compare the tenant's configured camps using live actor tagging.

    The old dashboard read ``Mention.coalition``, a seed-era field disconnected
    from the actor/camp configuration screen and live ingestion. This selector
    deliberately uses ``PoliticalActor.camp`` and the actor assessments created
    at ingestion, so changing tenant configuration changes the analysis.
    """
    project = issue.project
    camps = list(Camp.objects.filter(project=project).prefetch_related("actors"))
    issue_mentions = Mention.objects.filter(issue=issue, is_political=True)
    total_political = issue_mentions.count()
    attributed_ids = issue_mentions.filter(
        political_actors__camp__project=project
    ).values_list("pk", flat=True).distinct()
    total_attributed = attributed_ids.count()
    unattributed_pct = (
        round(((total_political - total_attributed) / total_political) * 100)
        if total_political else 0
    )

    camp_data = []
    camp_querysets = {}
    for camp in camps:
        qs = issue_mentions.filter(political_actors__camp=camp).distinct()
        camp_querysets[camp.pk] = qs
        count = qs.count()
        assessments = ActorSentimentAssessment.objects.filter(
            mention__issue=issue,
            actor__project=project,
            actor__camp=camp,
        )
        assessment_total = assessments.count()
        sentiment_counts = {
            row["sentiment"]: row["n"]
            for row in assessments.values("sentiment").annotate(n=Count("id"))
        }
        if not assessment_total:
            assessment_total = count
            sentiment_counts = {
                row["sentiment"]: row["n"]
                for row in qs.values("sentiment").annotate(n=Count("id"))
            }
        sentiment_breakdown = []
        for key, label in SENTIMENT_LABELS.items():
            c = sentiment_counts.get(key, 0)
            pct = round((c / assessment_total) * 100) if assessment_total else 0
            sentiment_breakdown.append({"key": key, "label": label, "pct": pct})
        actor_rows = list(
            PoliticalActor.objects.filter(project=project, camp=camp, is_active=True)
            .annotate(
                mention_count=Count(
                    "mentions",
                    filter=Q(mentions__issue=issue),
                    distinct=True,
                )
            )
            .order_by("-mention_count", "name")
        )
        camp_data.append({
            "camp": camp,
            "count": count,
            "assessment_count": assessment_total,
            "sentiment_breakdown": sentiment_breakdown,
            "dominant_themes": _dominant_themes(qs),
            "trend_chart": _series_trend(qs),
            "actors": actor_rows,
        })

    # A mention can reference actors from multiple camps. Share of Voice is
    # therefore normalized over camp attributions, rather than pretending the
    # camps are mutually exclusive and allowing the bar to exceed 100%.
    attribution_total = sum(item["count"] for item in camp_data)
    for item in camp_data:
        item["share_pct"] = (
            round(item["count"] / attribution_total * 100)
            if attribution_total else 0
        )
    _add_shared_scale_overlay(camp_data, camp_querysets)

    return {
        "issue": issue,
        "total_political": total_political,
        "total_attributed": total_attributed,
        "unattributed_pct": unattributed_pct,
        "camps": camp_data,
        "configured_actor_count": PoliticalActor.objects.filter(
            project=project, is_active=True
        ).count(),
        "overlay_chart": {"width": 1160, "height": 150},
    }


def _add_shared_scale_overlay(camp_data, camp_querysets, days=30, width=1160, height=150):
    """Attach trend points using one y-axis for every camp."""
    since = timezone.now() - timezone.timedelta(days=days)
    daily_by_camp = {}
    for item in camp_data:
        camp = item["camp"]
        daily = [0] * days
        for mention in camp_querysets[camp.pk].filter(posted_at__gte=since).only("posted_at"):
            offset = (mention.posted_at - since).days
            if 0 <= offset < days:
                daily[offset] += 1
        daily_by_camp[camp.pk] = daily

    max_value = max(
        (max(values) for values in daily_by_camp.values() if values),
        default=1,
    ) or 1
    for item in camp_data:
        item["overlay_points"] = _scale_points(
            daily_by_camp[item["camp"].pk], width, height, max_value
        )


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


def _series_trend(qs, days=30, width=560, height=90):
    since = timezone.now() - timezone.timedelta(days=days)
    daily = [0] * days
    for mention in qs.filter(posted_at__gte=since).only("posted_at"):
        offset = (mention.posted_at - since).days
        if 0 <= offset < days:
            daily[offset] += 1
    max_value = max(daily) or 1
    return {"points": _scale_points(daily, width, height, max_value), "width": width, "height": height}


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
    last ``days`` days as graph nodes. Edges are only created from observed
    reply/comment relationships or a reviewed coordination-detection cluster;
    thematic similarity alone is not presented as an interaction.

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

    # Accounts sitting inside a currently actionable coordination cluster.
    from apps.coordination.models import ClusterAccount, CoordinationCluster

    actionable_statuses = [
        CoordinationCluster.STATUS_FLAGGED,
        CoordinationCluster.STATUS_ESCALATED,
    ]
    clusters = list(
        CoordinationCluster.objects.filter(
            issue__project=project,
            status__in=actionable_statuses,
            accounts__handle__in=handles,
        )
        .prefetch_related("accounts")
        .distinct()
    )
    coordinated = set(
        ClusterAccount.objects.filter(
            cluster__issue__project=project,
            cluster__status__in=actionable_statuses,
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

    # Build real observed relationships. A reply is an explicit interaction.
    # A coordination edge is grounded in the detection module's persisted,
    # human-reviewable cluster evidence.
    node_by_handle = {node["handle"]: node for node in nodes}
    edge_map = {}

    def add_edge(handle_a, handle_b, *, replies=0, cluster_code=""):
        if (
            not handle_a
            or not handle_b
            or handle_a == handle_b
            or handle_a not in node_by_handle
            or handle_b not in node_by_handle
        ):
            return
        pair = tuple(sorted((handle_a, handle_b)))
        edge = edge_map.setdefault(
            pair,
            {"replies": 0, "cluster_codes": set()},
        )
        edge["replies"] += replies
        if cluster_code:
            edge["cluster_codes"].add(cluster_code)

    reply_rows = (
        qs.filter(
            parent__isnull=False,
            author_handle__in=handles,
            parent__author_handle__in=handles,
        )
        .values("author_handle", "parent__author_handle")
        .annotate(n=Count("id"))
    )
    for row in reply_rows:
        add_edge(
            row["author_handle"],
            row["parent__author_handle"],
            replies=row["n"],
        )

    for cluster in clusters:
        accounts = [
            account for account in cluster.accounts.all()
            if account.handle in node_by_handle
        ]
        hubs = [
            account for account in accounts
            if account.role == ClusterAccount.ROLE_HUB
        ]
        if hubs:
            for hub in hubs:
                for account in accounts:
                    add_edge(hub.handle, account.handle, cluster_code=cluster.cluster_code)
        else:
            for index, account in enumerate(accounts):
                for peer in accounts[index + 1:]:
                    add_edge(
                        account.handle,
                        peer.handle,
                        cluster_code=cluster.cluster_code,
                    )

    edges = []
    for (handle_a, handle_b), evidence in edge_map.items():
        a = node_by_handle[handle_a]
        b = node_by_handle[handle_b]
        labels = []
        if evidence["replies"]:
            labels.append(f"{evidence['replies']} balasan/komentar")
        if evidence["cluster_codes"]:
            labels.append(
                "bukti klaster " + ", ".join(sorted(evidence["cluster_codes"]))
            )
        weight = evidence["replies"] + len(evidence["cluster_codes"])
        edges.append({
            "x1": a["x"],
            "y1": a["y"],
            "x2": b["x"],
            "y2": b["y"],
            "coordinated": bool(evidence["cluster_codes"]),
            "width": round(min(4.5, 1 + math.log1p(weight)), 2),
            "evidence": " · ".join(labels),
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


def _sentiment_stats(qs):
    total = qs.count()
    counts = {
        row["sentiment"]: row["n"]
        for row in qs.values("sentiment").annotate(n=Count("id"))
    }
    breakdown = []
    for key, label in SENTIMENT_LABELS.items():
        count = counts.get(key, 0)
        breakdown.append({
            "key": key,
            "label": label,
            "count": count,
            "pct": round((count / total) * 100) if total else 0,
        })
    dominant = max(breakdown, key=lambda row: row["count"]) if total else {
        "key": Mention.SENTIMENT_NEUTRAL, "label": "Netral", "count": 0, "pct": 0,
    }
    return {"total": total, "breakdown": breakdown, "dominant": dominant}


def _daily_timeline_for_dates(qs, start_date, end_date):
    days = (end_date - start_date).days + 1
    buckets = OrderedDict(
        (
            start_date + timezone.timedelta(days=offset),
            {"positive": 0, "neutral": 0, "negative": 0},
        )
        for offset in range(days)
    )
    for mention in qs.only("posted_at", "sentiment"):
        day = timezone.localtime(mention.posted_at).date()
        if day in buckets:
            buckets[day][mention.sentiment] += 1
    return list(buckets.values()), list(buckets.keys())


def _channel_rows(qs):
    rows = []
    for key, label in Platform.CHANNEL_CHOICES:
        channel_qs = qs.filter(platform__channel_type=key)
        stats = _sentiment_stats(channel_qs)
        if stats["total"] or key in (Platform.CHANNEL_NEWS, Platform.CHANNEL_SOCIAL):
            rows.append({
                "key": key,
                "label": label,
                "count": stats["total"],
                "sentiment_breakdown": stats["breakdown"],
                "dominant": stats["dominant"],
            })
    combined = _sentiment_stats(qs)
    rows.append({
        "key": "combined",
        "label": "Gabungan",
        "count": combined["total"],
        "sentiment_breakdown": combined["breakdown"],
        "dominant": combined["dominant"],
    })
    return rows


def _top_evidence(qs, limit=3):
    evidence = []
    seen_urls = set()
    candidates = qs.select_related("platform").order_by("-engagement_count", "-posted_at")
    for mention in candidates[: max(limit * 8, 20)]:
        snippet = (mention.content_snippet or "").strip()
        # Core PDF fonts cannot render many emoji-only comments; a blank-looking
        # evidence bullet is less informative than the next textual comment.
        if not any(character.isalnum() for character in snippet):
            continue
        url = mention.source_url or ""
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        evidence.append({
            "id": mention.id,
            "snippet": snippet,
            "source_url": url,
            "clickable": mention.has_clickable_source,
            "domain": urlsplit(url).hostname or "" if url else "",
            "platform": mention.platform.display_name,
            "posted_at": mention.posted_at,
            "sentiment": mention.sentiment,
            "engagement": mention.engagement_count,
        })
        if len(evidence) >= limit:
            break
    return evidence


def _issue_rows(qs, total_mentions, limit=8):
    aggregate_rows = list(
        qs.filter(issue_label__isnull=False)
        .values("issue_label__issue_id", "issue_label__issue__name")
        .annotate(
            count=Count("id"),
            positive=Count("id", filter=Q(sentiment=Mention.SENTIMENT_POSITIVE)),
            neutral=Count("id", filter=Q(sentiment=Mention.SENTIMENT_NEUTRAL)),
            negative=Count("id", filter=Q(sentiment=Mention.SENTIMENT_NEGATIVE)),
            first_seen=Min("posted_at"),
            last_seen=Max("posted_at"),
        )
        .order_by("-count")[:limit]
    )
    issues = []
    for row in aggregate_rows:
        issue_qs = qs.filter(issue_label__issue_id=row["issue_label__issue_id"])
        count = row["count"]
        breakdown = [
            {"key": key, "label": label, "count": row[key],
             "pct": round((row[key] / count) * 100) if count else 0}
            for key, label in SENTIMENT_LABELS.items()
        ]
        dominant = max(breakdown, key=lambda item: item["count"])
        actor_rows = list(
            PoliticalActor.objects.filter(mentions__in=issue_qs)
            .annotate(n=Count("mentions", distinct=True))
            .order_by("-n")
            .values("name", "n")[:4]
        )
        issues.append({
            "id": row["issue_label__issue_id"],
            "name": row["issue_label__issue__name"],
            "count": count,
            "share_pct": round((count / total_mentions) * 100) if total_mentions else 0,
            "sentiment_breakdown": breakdown,
            "dominant": dominant,
            "negative_pct": next(item["pct"] for item in breakdown if item["key"] == "negative"),
            "positive_pct": next(item["pct"] for item in breakdown if item["key"] == "positive"),
            "first_seen": row["first_seen"],
            "last_seen": row["last_seen"],
            "actors": actor_rows,
            "evidence": _top_evidence(issue_qs),
        })
    return issues


def _actor_rows(qs, project):
    rows = []
    for actor in PoliticalActor.objects.filter(project=project, is_active=True):
        assessments = ActorSentimentAssessment.objects.filter(
            actor=actor, mention__in=qs
        )
        actor_qs = qs.filter(actor_sentiments__in=assessments).distinct()
        total = assessments.count()
        counts = {
            row["sentiment"]: row["n"]
            for row in assessments.values("sentiment").annotate(n=Count("id"))
        }
        breakdown = [
            {
                "key": key,
                "label": label,
                "count": counts.get(key, 0),
                "pct": round((counts.get(key, 0) / total) * 100) if total else 0,
            }
            for key, label in SENTIMENT_LABELS.items()
        ]
        dominant = max(breakdown, key=lambda row: row["count"]) if total else {
            "key": Mention.SENTIMENT_NEUTRAL,
            "label": "Netral",
            "count": 0,
            "pct": 0,
        }
        top_issue = (
            actor_qs.filter(issue_label__isnull=False)
            .values("issue_label__issue__name")
            .annotate(n=Count("id"))
            .order_by("-n")
            .first()
        )
        rows.append({
            "actor": actor,
            "count": total,
            "sentiment_breakdown": breakdown,
            "dominant": dominant,
            "top_issue": top_issue["issue_label__issue__name"] if top_issue else "",
            "evidence": _top_evidence(actor_qs, limit=2),
            "manual_count": assessments.filter(
                source=ActorSentimentAssessment.SOURCE_MANUAL
            ).count(),
        })
    rows.sort(key=lambda row: (-row["count"], row["actor"].name))
    return rows


def _source_inventory(qs, project):
    domain_map = {}
    cited_mentions = 0
    unique_urls = set()
    for row in qs.exclude(source_url__isnull=True).exclude(source_url="").values(
        "source_url", "platform__display_name"
    ):
        url = row["source_url"]
        host = (urlsplit(url).hostname or "").lower()
        if not host or host == "demo.pantau.local":
            continue
        cited_mentions += 1
        unique_urls.add(url)
        item = domain_map.setdefault(
            host, {"domain": host, "count": 0, "platforms": set(), "urls": []}
        )
        item["count"] += 1
        item["platforms"].add(row["platform__display_name"])
        if len(item["urls"]) < 3 and url not in item["urls"]:
            item["urls"].append(url)

    sources = sorted(domain_map.values(), key=lambda item: (-item["count"], item["domain"]))
    for item in sources:
        item["platforms"] = ", ".join(sorted(item["platforms"]))

    from apps.governance.models import MonitoredDomain

    configured = list(
        MonitoredDomain.objects.filter(project=project, status=MonitoredDomain.STATUS_ACTIVE)
        .order_by("domain")
        .values("domain", "adapter", "feed_url")
    )
    observed_hosts = set(domain_map)
    configured_hosts = {row["domain"].lower().removeprefix("www.") for row in configured}
    for row in configured:
        normalized = row["domain"].lower().removeprefix("www.")
        row["observed"] = any(
            host.removeprefix("www.") == normalized
            or host.removeprefix("www.").endswith("." + normalized)
            for host in observed_hosts
        )
    observed_not_configured = [
        item for item in sources
        if not any(
            item["domain"].removeprefix("www.") == configured_host
            or item["domain"].removeprefix("www.").endswith("." + configured_host)
            for configured_host in configured_hosts
        )
    ]
    return {
        "sources": sources,
        "configured": configured,
        "observed_not_configured": observed_not_configured,
        "cited_mentions": cited_mentions,
        "unique_urls": len(unique_urls),
        "coverage_pct": round((cited_mentions / qs.count()) * 100) if qs.count() else 0,
    }


def _potential_keywords(qs, project, issue_rows):
    from apps.governance.models import MonitoringKeyword

    active_terms = {
        term.strip().lower()
        for term in MonitoringKeyword.objects.filter(project=project, is_active=True)
        .values_list("keyword", flat=True)
        if term.strip()
    }
    candidates = {}

    def add(kind, term, source, matches, reason):
        clean = (term or "").strip()
        normalized = clean.lower().lstrip("#@")
        if not clean or normalized in {value.lstrip("#@") for value in active_terms}:
            return
        key = (kind, normalized)
        current = candidates.get(key)
        if current is None or matches > current["matches"]:
            candidates[key] = {
                "kind": kind,
                "term": clean,
                "source": source,
                "matches": matches,
                "reason": reason,
                "priority": "Tinggi" if matches >= 10 else "Sedang" if matches else "Eksplorasi",
            }

    for actor in PoliticalActor.objects.filter(project=project, is_active=True):
        matches = qs.filter(political_actors=actor).distinct().count()
        for term in [*(actor.keywords or []), *(actor.handles or [])]:
            add("Aktor", term, actor.name, matches, "Alias/akun aktor yang sudah muncul pada pemantauan.")

    for program in GovernmentProgram.objects.filter(project=project, is_active=True):
        matches = qs.filter(program=program).count()
        for term in program.keywords or []:
            add("Program", term, program.name, matches, "Istilah program untuk memperluas recall koleksi.")

    issues_by_id = {issue["id"]: issue for issue in issue_rows}
    for issue in Issue.objects.filter(id__in=issues_by_id):
        matches = issues_by_id[issue.id]["count"]
        for term in issue.keywords or []:
            add("Topik", term, issue.name, matches, "Kata pemicu topik dominan pada periode laporan.")

    return sorted(
        candidates.values(),
        key=lambda item: (-item["matches"], item["kind"], item["term"].lower()),
    )[:24]


def _report_recommendations(total_mentions, sentiment, channel_rows, actor_rows, issue_rows,
                            source_inventory, taxonomy_coverage_pct):
    recommendations = []
    if not total_mentions:
        return [{
            "title": "Aktifkan dan verifikasi koleksi",
            "detail": "Tidak ada sebutan pada rentang laporan. Periksa jadwal, kata kunci, dan kesehatan kolektor sebelum menarik kesimpulan.",
            "basis": "0 sebutan teramati",
        }]

    negative = next(row for row in sentiment["breakdown"] if row["key"] == "negative")
    if issue_rows:
        issue = max(issue_rows, key=lambda item: (item["negative_pct"], item["count"]))
        if issue["negative_pct"] >= 40:
            recommendations.append({
                "title": f"Prioritaskan respons untuk {issue['name']}",
                "detail": "Siapkan pernyataan faktual dan empatik, tunjukkan tindakan yang sudah dilakukan, lalu perbarui bukti secara berkala.",
                "basis": f"{issue['count']} sebutan; {issue['negative_pct']}% negatif",
            })

    news = next((row for row in channel_rows if row["key"] == Platform.CHANNEL_NEWS), None)
    social = next((row for row in channel_rows if row["key"] == Platform.CHANNEL_SOCIAL), None)
    if news and social and news["count"] and social["count"]:
        news_neg = next(r["pct"] for r in news["sentiment_breakdown"] if r["key"] == "negative")
        social_neg = next(r["pct"] for r in social["sentiment_breakdown"] if r["key"] == "negative")
        if social_neg >= news_neg + 10:
            recommendations.append({
                "title": "Perkuat respons di media sosial",
                "detail": "Prioritaskan social listening, FAQ singkat, dan respons cepat pada keluhan terverifikasi; jangan menganggap nada media online mewakili reaksi publik.",
                "basis": f"Negatif media sosial {social_neg}% vs media online {news_neg}%",
            })

    active_actor_rows = [row for row in actor_rows if row["count"]]
    if active_actor_rows:
        actor = max(
            active_actor_rows,
            key=lambda item: next(
                row["pct"] for row in item["sentiment_breakdown"] if row["key"] == "negative"
            ),
        )
        actor_negative = next(
            row["pct"] for row in actor["sentiment_breakdown"] if row["key"] == "negative"
        )
        if actor_negative >= 40:
            recommendations.append({
                "title": f"Lindungi reputasi {actor['actor'].name} dengan bukti langsung",
                "detail": "Tentukan juru bicara, pesan inti, dan bukti pendukung per isu; tinjau sentimen khusus aktor sebelum publikasi.",
                "basis": f"{actor['count']} sebutan terkait; {actor_negative}% negatif",
            })

    positive_issues = [row for row in issue_rows if row["positive_pct"] >= 40]
    if positive_issues and negative["pct"] >= 35:
        positive = max(positive_issues, key=lambda item: item["count"])
        recommendations.append({
            "title": f"Pertahankan agenda positif {positive['name']}",
            "detail": "Publikasikan secara proporsional setelah kebutuhan komunikasi krisis terpenuhi agar tidak terbaca sebagai pengalihan isu.",
            "basis": f"{positive['count']} sebutan; {positive['positive_pct']}% positif",
        })

    if source_inventory["coverage_pct"] < 70:
        recommendations.append({
            "title": "Naikkan keterlacakan sumber",
            "detail": "Wajibkan URL kanonik pada ingestion dan jangan finalisasi klaim yang tidak dapat ditelusuri ke artikel/unggahan asal.",
            "basis": f"Hanya {source_inventory['coverage_pct']}% sebutan memiliki URL sumber yang dapat diklik",
        })
    if taxonomy_coverage_pct < 80:
        recommendations.append({
            "title": "Tuntaskan pelabelan topik",
            "detail": "Tinjau antrean taksonomi dan tambahkan alias topik agar isu dominan tidak tersebar sebagai tema bebas.",
            "basis": f"Cakupan taksonomi {taxonomy_coverage_pct}%",
        })

    recommendations.append({
        "title": "Wajibkan tinjauan analis sebelum PDF diedarkan",
        "detail": "Periksa angka, sentimen per aktor, kronologi, kutipan, dan rekomendasi. PDF adalah draf analitis sampai ditinjau manusia.",
        "basis": "Kontrol mutu dan akuntabilitas laporan",
    })
    return recommendations[:6]


def laporan_summary(project, days=30, start_date=None, end_date=None):
    """Evidence-backed periodic media analysis used by both the report center and
    the server-generated PDF. Dates are inclusive, making a 21-27 July report
    reproducible instead of tied to the day the analyst happens to open the page."""
    end_date = end_date or timezone.localdate()
    start_date = start_date or (end_date - timezone.timedelta(days=days - 1))
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    days = (end_date - start_date).days + 1

    qs = Mention.objects.filter(
        project=project,
        posted_at__date__gte=start_date,
        posted_at__date__lte=end_date,
    )
    sentiment = _sentiment_stats(qs)
    total_mentions = sentiment["total"]
    platform_rows = []
    for row in qs.values(
        "platform__display_name", "platform__channel_type"
    ).annotate(n=Count("id")).order_by("-n"):
        platform_rows.append({
            "name": row["platform__display_name"],
            "channel_type": row["platform__channel_type"],
            "count": row["n"],
            "pct": round((row["n"] / total_mentions) * 100) if total_mentions else 0,
        })

    timeline, dates = _daily_timeline_for_dates(qs, start_date, end_date)
    issue_rows = _issue_rows(qs, total_mentions)
    actor_rows = _actor_rows(qs, project)
    channel_rows = _channel_rows(qs)
    source_inventory = _source_inventory(qs, project)
    labeled_count = qs.filter(issue_label__isnull=False).count()
    taxonomy_coverage_pct = round((labeled_count / total_mentions) * 100) if total_mentions else 0
    avg_confidence = qs.aggregate(value=Avg("sentiment_confidence"))["value"] or 0
    manual_count = qs.filter(sentiment_model="manual").count()
    collected_count = qs.filter(is_scraped=True).count()
    seeded_count = total_mentions - collected_count
    post_qs = qs.filter(content_type=Mention.CONTENT_POST)
    comment_qs = qs.filter(content_type=Mention.CONTENT_COMMENT)
    comment_sentiment = _sentiment_stats(comment_qs)
    eligible_comment_parents = post_qs.filter(
        platform__channel_type=Platform.CHANNEL_SOCIAL,
        reported_comment_count__gt=0,
    )
    analyzed_parent_ids = set(
        comment_qs.exclude(parent_id__isnull=True).values_list("parent_id", flat=True)
    )
    eligible_parent_count = eligible_comment_parents.count()
    comment_parent_coverage_pct = (
        round(
            eligible_comment_parents.filter(id__in=analyzed_parent_ids).count()
            / eligible_parent_count * 100
        )
        if eligible_parent_count else 0
    )
    comment_platform_rows = list(
        comment_qs.values("platform__display_name")
        .annotate(n=Count("id"))
        .order_by("-n")
    )
    comment_analysis = {
        "count": comment_sentiment["total"],
        "parent_count": len(analyzed_parent_ids),
        "eligible_parent_count": eligible_parent_count,
        "parent_coverage_pct": comment_parent_coverage_pct,
        "reported_comment_count": (
            eligible_comment_parents.aggregate(total=Sum("reported_comment_count"))["total"] or 0
        ),
        "sentiment_breakdown": comment_sentiment["breakdown"],
        "dominant": comment_sentiment["dominant"],
        "platform_rows": comment_platform_rows,
        "issue_rows": _issue_rows(comment_qs, comment_sentiment["total"], limit=5),
        "evidence": _top_evidence(comment_qs, limit=5),
    }
    potential_keywords = _potential_keywords(qs, project, issue_rows)
    recommendations = _report_recommendations(
        total_mentions, sentiment, channel_rows, actor_rows, issue_rows,
        source_inventory, taxonomy_coverage_pct,
    )
    if eligible_parent_count and comment_parent_coverage_pct < 70:
        recommendations.insert(-1, {
            "title": "Perluas sampel komentar publik",
            "detail": "Koleksi isi komentar dari posting berengagement tinggi pada setiap platform, dengan batas biaya dan retensi yang terdokumentasi.",
            "basis": (
                f"Baru {comment_parent_coverage_pct}% posting yang memiliki komentar terlapor "
                "mempunyai sampel komentar teranalisis"
            ),
        })
        recommendations = recommendations[:6]

    briefs = list(DailyBrief.objects.filter(project=project).order_by("-brief_date")[:30])
    final_count = sum(1 for brief in briefs if brief.status == DailyBrief.STATUS_FINAL)
    return {
        "days": days,
        "period_start": start_date,
        "period_end": end_date,
        "total_mentions": total_mentions,
        "total_reach": qs.aggregate(total=Sum("reach_estimate"))["total"] or 0,
        "unique_authors": qs.values("author_handle").distinct().count(),
        "sentiment_breakdown": sentiment["breakdown"],
        "dominant_sentiment": sentiment["dominant"],
        "channel_rows": channel_rows,
        "platform_rows": platform_rows,
        "top_themes": _dominant_themes(qs, limit=6),
        "issue_rows": issue_rows,
        "actor_rows": actor_rows,
        "comment_analysis": comment_analysis,
        "source_inventory": source_inventory,
        "potential_keywords": potential_keywords,
        "recommendations": recommendations,
        "timeline_chart": timeline_chart(timeline, width=1160, height=180, dates=dates),
        "quality": {
            "source_coverage_pct": source_inventory["coverage_pct"],
            "taxonomy_coverage_pct": taxonomy_coverage_pct,
            "avg_sentiment_confidence_pct": round(avg_confidence * 100),
            "manual_sentiment_count": manual_count,
            "cited_mentions": source_inventory["cited_mentions"],
            "unique_urls": source_inventory["unique_urls"],
            "post_count": post_qs.count(),
            "comment_count": comment_sentiment["total"],
            "comment_parent_coverage_pct": comment_parent_coverage_pct,
            "collected_count": collected_count,
            "seeded_count": seeded_count,
        },
        "methodology_notes": [
            "Semua persentase dihitung dari sebutan yang benar-benar tersimpan pada rentang tanggal inklusif; tidak ada pembobotan sentimen sosial yang diasumsikan.",
            "Media Online, Media Sosial, dan Sumber Lain dipisahkan melalui klasifikasi kanal pada setiap platform.",
            "Komentar publik yang berhasil dikoleksi dianalisis sebagai unit tersendiri dan ditautkan ke posting induknya; jumlah komentar tidak dipakai sebagai pengganti isi komentar.",
            "Sentimen aktor disimpan per pasangan sebutan-aktor, sehingga satu artikel dapat dinilai berbeda terhadap institusi dan pejabat yang disebut; nilai otomatis tetap wajib ditinjau.",
            "Isu diprioritaskan dari taksonomi terstruktur, lalu ditautkan ke bukti sumber berengagement tertinggi.",
            (
                f"Provenansi korpus: {collected_count} sebutan hasil koleksi dan "
                f"{seeded_count} sebutan fixture/demo."
            ),
        ],
        "limitations": [
            "Percakapan privat, konten yang dihapus, dan sumber yang tidak didukung kolektor tidak termasuk.",
            "Proporsi menggambarkan korpus yang terkoleksi, bukan sensus seluruh opini publik.",
            (
                f"{100 - source_inventory['coverage_pct']}% sebutan tidak memiliki URL sumber yang "
                "dapat diverifikasi; angka agregatnya tetap dihitung tetapi tidak layak dijadikan kutipan."
            ),
            (
                f"{100 - taxonomy_coverage_pct}% sebutan belum memiliki label isu terstruktur dan "
                "dapat mengurangi ketepatan pemeringkatan topik."
            ),
            (
                f"Komentar telah dikoleksi dari {comment_parent_coverage_pct}% posting publik "
                "yang melaporkan adanya komentar pada periode ini."
                if eligible_parent_count
                else "Tidak ada posting dengan komentar terlapor pada periode ini; sentimen komentar tidak dapat digeneralisasi."
            ),
            *(
                [
                    f"{seeded_count} sebutan fixture/demo masih berada pada proyek ini; "
                    "PDF tidak boleh diperlakukan sebagai laporan produksi sebelum fixture "
                    "dipisahkan dari korpus hasil koleksi."
                ]
                if seeded_count else []
            ),
        ],
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

    queryset = queryset.prefetch_related("escalations")
    confirmed = _attach_escalation(list(queryset.filter(is_confirmed=True)))
    candidates = _attach_escalation(list(queryset.filter(is_confirmed=False)))

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


def _attach_escalation(incidents):
    """Attach each incident's newest escalation assessment for template use.

    Sorting the board by escalation score is done in Python rather than SQL: the
    board is at most a few dozen rows, and a window function over the assessment
    table would obscure the far more important property that an incident *without*
    an assessment still has to appear, ranked by its existing severity.
    """
    for incident in incidents:
        assessments = list(incident.escalations.all())
        incident.escalation = (
            max(assessments, key=lambda a: a.computed_at) if assessments else None
        )
    incidents.sort(
        key=lambda i: (
            -(i.escalation.score if i.escalation else -1),
            i.severity_rank,
            -i.mention_count,
        )
    )
    return incidents


def incident_attribution(incident):
    """Who the mentions behind one incident are actually blaming.

    Turns attribution into routing: the dominant OPD-level target becomes the
    suggested assignment, so the board proposes the dinas the public is naming
    rather than leaving an operator to infer it from the incident title.
    """
    rows = (
        MentionAttribution.objects.filter(
            mention__incidents=incident, sentiment=Mention.SENTIMENT_NEGATIVE
        )
        .select_related("target", "target__opd", "target__parent")
    )
    total = rows.count()
    if not total:
        return {"total": 0, "targets": [], "suggested_opd": None}

    tally = {}
    for row in rows:
        entry = tally.setdefault(
            row.target.id,
            {"target": row.target, "count": 0, "confidences": []},
        )
        entry["count"] += 1
        entry["confidences"].append(row.confidence)

    targets = []
    for entry in sorted(tally.values(), key=lambda e: -e["count"]):
        target = entry["target"]
        confidence, low_pct = confidence_stats(entry["confidences"])
        targets.append({
            "name": target.name,
            "is_own_government": target.counts_as_own_government,
            "metric": Metric(
                value=round((entry["count"] / total) * 100),
                unit="percent",
                label=f"kritik negatif ke {target.name}",
                method=(
                    f"atribusi negatif ke {target.name} ÷ seluruh atribusi negatif "
                    f"pada sebutan insiden ini ({total} baris)"
                ),
                evidence=EvidenceRef(
                    "attribution",
                    {"target": target.id, "sentiment": Mention.SENTIMENT_NEGATIVE},
                ),
                contributing=entry["count"],
                confidence=confidence,
                low_confidence_pct=low_pct,
            ),
        })

    suggested = next(
        (
            entry["target"].opd
            for entry in sorted(tally.values(), key=lambda e: -e["count"])
            if entry["target"].opd is not None
        ),
        None,
    )
    return {"total": total, "targets": targets, "suggested_opd": suggested}
