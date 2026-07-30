"""Repair `PlatformIntegration.actor_id` rows that cannot address an Apify Actor.

Databases seeded before the connector switched to pinned public Actors hold opaque
object IDs (`culc72xb7MP3EbaeX`) or console paths (`apify/instagram-scraper`) in this
column. Both override the correct default at collection time, and neither resolves:
an object ID stops existing once its Actor is renamed or removed (HTTP 404
`record-not-found` / "Actor was not found"), and a console path is not a valid API
path at all (HTTP 404 `page-not-found`). Every enabled source then fails.

The reference map is frozen here on purpose: a migration must keep meaning even
after `apify_crawler.ACTOR_CONFIG` is changed again, so it is not imported.

Only `method="apify"` rows are touched — an internal-method row legitimately stores
a human note ("scraper internal v2.4.1") rather than an Actor reference.
"""
import re

from django.db import migrations

ACTOR_REFERENCE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*~[A-Za-z0-9][A-Za-z0-9_.-]*")

PINNED_ACTORS = {
    "x": "apidojo~tweet-scraper",
    "facebook": "scraper_one~facebook-posts-search",
    "youtube": "streamers~youtube-scraper",
    "tiktok": "clockworks~tiktok-scraper",
    "instagram": "apify~instagram-scraper",
}


def repair(apps, schema_editor):
    PlatformIntegration = apps.get_model("governance", "PlatformIntegration")
    repaired = []
    for integration in PlatformIntegration.objects.filter(
        method="apify"
    ).select_related("platform"):
        candidate = (integration.actor_id or "").strip().replace("/", "~")
        if ACTOR_REFERENCE_RE.fullmatch(candidate):
            # Already usable, or a console path we can convert without guessing.
            if candidate == integration.actor_id:
                continue
        else:
            candidate = PINNED_ACTORS.get(integration.platform.slug, "")
            if not candidate:
                # Unknown platform: blanking is safe — the connector then falls
                # back to its own default instead of calling a dead reference.
                candidate = ""
        integration.actor_id = candidate
        repaired.append(integration)
    PlatformIntegration.objects.bulk_update(repaired, ["actor_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("governance", "0011_manualcollectionrequest_history_window"),
    ]

    operations = [
        # Irreversible by intent: the previous values are precisely the broken ones.
        migrations.RunPython(repair, migrations.RunPython.noop),
    ]
