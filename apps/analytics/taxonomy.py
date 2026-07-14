"""Issue Taxonomy services (FR-3A): auto/manual labeling, the manual review
queue, and issue merge/unmerge with a reversible audit trail.
"""
from django.db import transaction
from django.utils import timezone

from .models import Issue, IssueLabel, IssueMergeHistory, Mention


def match_issue(text):
    """Return the first active Issue whose keyword appears in ``text`` (FR-3A.2)."""
    text = (text or "").lower()
    for issue in Issue.objects.filter(is_active=True):
        if any(kw.lower() in text for kw in (issue.keywords or [])):
            return issue
    return None


def auto_label(mention):
    """Auto-assign an Issue to a mention. Never overwrites a manual decision
    (FR-3A.3). Returns the IssueLabel, or None if nothing matched."""
    existing = IssueLabel.objects.filter(mention=mention).first()
    if existing and existing.source == IssueLabel.SOURCE_MANUAL:
        return existing

    issue = match_issue(mention.content_snippet)
    if issue is None:
        return None
    label, _ = IssueLabel.objects.update_or_create(
        mention=mention,
        defaults={"issue": issue, "source": IssueLabel.SOURCE_AUTO, "decided_by": "sistem"},
    )
    return label


def assign_issue(mention, issue, by):
    """Manually assign/correct a mention's Issue (FR-3A.3)."""
    label, _ = IssueLabel.objects.update_or_create(
        mention=mention,
        defaults={"issue": issue, "source": IssueLabel.SOURCE_MANUAL, "decided_by": by},
    )
    return label


def review_queue(project):
    """Mentions in a project that have not been confidently labeled yet (FR-3A.3)."""
    return Mention.objects.filter(project=project, issue_label__isnull=True)


def preview_top_content(issue, limit=5):
    """Top content for an Issue, to confirm a merge before committing (FR-3A.6)."""
    return list(
        Mention.objects.filter(issue_label__issue=issue).order_by("-engagement_count")[:limit]
    )


@transaction.atomic
def merge_issues(source_issue_ids, target_id, performed_by):
    """Merge one or more Issues into a target: move all labels, deactivate the
    redundant Issues, and record enough state to support unmerge (FR-3A.5)."""
    moved = {}
    for sid in source_issue_ids:
        if sid == target_id:
            continue
        mention_ids = list(
            IssueLabel.objects.filter(issue_id=sid).values_list("mention_id", flat=True)
        )
        moved[str(sid)] = mention_ids
        IssueLabel.objects.filter(issue_id=sid).update(issue_id=target_id)
        Issue.objects.filter(id=sid).update(is_active=False)

    return IssueMergeHistory.objects.create(
        source_issue_ids=list(source_issue_ids),
        target_issue_id=target_id,
        moved=moved,
        performed_by=performed_by,
    )


@transaction.atomic
def unmerge(history):
    """Reverse a prior merge (FR-3A.5)."""
    if history.reversed_at is not None:
        return history
    for sid, mention_ids in history.moved.items():
        Issue.objects.filter(id=int(sid)).update(is_active=True)
        IssueLabel.objects.filter(mention_id__in=mention_ids).update(issue_id=int(sid))
    history.reversed_at = timezone.now()
    history.save(update_fields=["reversed_at"])
    return history
