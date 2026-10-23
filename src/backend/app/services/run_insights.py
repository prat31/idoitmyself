"""Read-only analysis of one run, built from what's stored: the run's label/inbox snapshots, the model
answers attributed to it (`label_evaluations.run_id`) and the labels it applied (`email_labels.run_id`).

Provenance caveat: when a later run re-asks the same (email, label), the answer is re-attributed to
that run, so older runs keep their totals but can lose per-email detail. Runs from before answers
were stored (migration 0009) have totals only."""

import uuid
from datetime import timedelta
from typing import Literal

from sqlalchemy import Select, case, exists, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email import Email, EmailLabel, LabelEvaluation, condition_hash
from app.models.inbox import Inbox
from app.models.label import Label
from app.models.run import Run
from app.schemas.run import (
    ProbabilityBucket,
    RunEmailLabel,
    RunEmailPage,
    RunEmailRow,
    RunInsights,
    RunLabelInsight,
    TimelineBucketOut,
)
from app.services.stats import _timeline, parse_timezone

NEAR_WINDOW = 0.1
HISTOGRAM_BUCKETS = 10

Tab = Literal["matched", "near", "not_matched", "skipped"]
Sort = Literal["probability_desc", "probability_asc", "sent_desc"]


async def run_insights(session: AsyncSession, run: Run, tz_name: str) -> RunInsights:
    tz = parse_timezone(tz_name)
    labels: list[RunLabelInsight] = []
    for rl in run.labels:
        current = await session.get(Label, rl.label_id) if rl.label_id else None
        evaluations = select(LabelEvaluation.probability).where(
            LabelEvaluation.run_id == run.id, LabelEvaluation.label_id == rl.label_id
        )
        probabilities = [row[0] for row in (await session.execute(evaluations)).all()] if rl.label_id else []
        counts = [0] * HISTOGRAM_BUCKETS
        for p in probabilities:
            counts[min(HISTOGRAM_BUCKETS - 1, int(p * HISTOGRAM_BUCKETS))] += 1
        labels.append(
            RunLabelInsight(
                label_id=rl.label_id,
                label_name=rl.label_name,
                color=current.color if current else None,
                filter_condition=rl.filter_condition,
                match_threshold=rl.match_threshold,
                condition_changed=current is None or (current.filter_condition or "") != rl.filter_condition,
                asked=len(probabilities),
                matched=rl.matched,
                near_threshold=sum(abs(p - rl.match_threshold) <= NEAR_WINDOW for p in probabilities),
                histogram=[
                    ProbabilityBucket(start=i / HISTOGRAM_BUCKETS, count=c) for i, c in enumerate(counts)
                ],
            )
        )

    applied_by_run = exists().where(EmailLabel.email_id == Email.id, EmailLabel.run_id == run.id)
    first = run.window_start.astimezone(tz).date()
    last = (run.window_end - timedelta(microseconds=1)).astimezone(tz).date()
    granularity, timeline = await _timeline(session, [applied_by_run], literal(True), tz, first, last)
    return RunInsights(
        near_window=NEAR_WINDOW,
        granularity=granularity,
        labels=labels,
        matched_timeline=[TimelineBucketOut(start=b.start, emails=b.emails) for b in timeline],
    )


async def run_emails(
    session: AsyncSession,
    run: Run,
    *,
    tab: Tab,
    label_id: uuid.UUID | None,
    sort: Sort,
    page: int,
    page_size: int,
) -> RunEmailPage:
    """(email, label) results for the run, one row per pair, filtered by tab and optionally a label."""
    specs = [rl for rl in run.labels if rl.label_id and (label_id is None or rl.label_id == label_id)]
    if not specs:
        return RunEmailPage(items=[], total=0, page=page, page_size=page_size)
    threshold = {rl.label_id: rl.match_threshold for rl in specs}
    inbox_ids = [ri.inbox_id for ri in run.inboxes if ri.inbox_id]

    # Per-label threshold (and condition fingerprint) as this run used them, available to SQL.
    threshold_expr = case(threshold, value=LabelEvaluation.label_id)
    hash_expr = case(
        {rl.label_id: condition_hash(rl.filter_condition) for rl in specs}, value=LabelEvaluation.label_id
    )

    base: Select = (
        select(
            Email, Inbox.name, LabelEvaluation.label_id, LabelEvaluation.probability, LabelEvaluation.run_id
        )
        .join(LabelEvaluation, LabelEvaluation.email_id == Email.id)
        .join(Inbox, Inbox.id == Email.inbox_id)
        .where(LabelEvaluation.label_id.in_(list(threshold)))
    )
    if tab == "skipped":
        # Answers from another run, for the same condition, that this run reused instead of asking.
        base = base.where(
            literal(not run.reclassify),  # a re-classify run reuses nothing
            LabelEvaluation.run_id.is_distinct_from(run.id),
            LabelEvaluation.condition_hash == hash_expr,
            Email.inbox_id.in_(inbox_ids),
            Email.sent_at >= run.window_start,
            Email.sent_at < run.window_end,
        )
    else:
        base = base.where(LabelEvaluation.run_id == run.id)
        if tab == "matched":
            base = base.where(LabelEvaluation.probability >= threshold_expr)
        elif tab == "not_matched":
            base = base.where(LabelEvaluation.probability < threshold_expr)
        elif tab == "near":
            base = base.where(func.abs(LabelEvaluation.probability - threshold_expr) <= NEAR_WINDOW)

    total = await session.scalar(select(func.count()).select_from(base.subquery()))
    order = {
        "probability_desc": [LabelEvaluation.probability.desc(), Email.sent_at.desc()],
        "probability_asc": [LabelEvaluation.probability.asc(), Email.sent_at.desc()],
        "sent_desc": [Email.sent_at.desc(), LabelEvaluation.probability.desc()],
    }[sort]
    rows = (
        await session.execute(base.order_by(*order, Email.id).offset((page - 1) * page_size).limit(page_size))
    ).all()

    labels = {rl.label_id: rl for rl in specs}
    colors = dict(
        (await session.execute(select(Label.id, Label.color).where(Label.id.in_(list(labels))))).all()
    )
    items = [
        RunEmailRow(
            email_id=email.id,
            inbox_name=inbox_name,
            sent_at=email.sent_at,
            from_address=email.from_address,
            subject=email.subject,
            snippet=email.snippet,
            result=RunEmailLabel(
                label_id=lid,
                label_name=labels[lid].label_name,
                color=colors.get(lid),
                probability=probability,
                matched=probability >= threshold[lid],
                from_this_run=answered_by == run.id,
            ),
        )
        for email, inbox_name, lid, probability, answered_by in rows
    ]
    return RunEmailPage(items=items, total=total or 0, page=page, page_size=page_size)
