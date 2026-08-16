from datetime import datetime, timezone

from job_finder.dashboard_metrics import (
    DashboardFilters,
    MetricAgendaEvent,
    MetricApplication,
    MetricApplicationEvent,
    MetricJob,
    MetricSearchRun,
    build_dashboard,
)


def at(day: int, hour: int = 10) -> datetime:
    return datetime(2026, 8, day, hour, tzinfo=timezone.utc)


def test_dashboard_uses_distinct_jobs_and_visible_denominators() -> None:
    jobs = [
        MetricJob(1, at(1), ("remoteok",)),
        MetricJob(2, at(2), ("remoteok", "other")),
        MetricJob(3, at(3), ("other",), deleted_at=at(3, 12)),
    ]
    applications = [
        MetricApplication(1, at(4), "interview"),
        MetricApplication(2, at(5), "rejected"),
    ]
    dashboard = build_dashboard(
        jobs,
        applications,
        [],
        [],
        DashboardFilters(at(1, 0), at(8, 0)),
    )

    assert dashboard["cards"] == {
        "jobs_found": 2,
        "applications": 2,
        "interviews": 1,
        "offers": 0,
        "hired": 0,
        "rejected": 1,
        "active_pipeline": 1,
    }
    funnel = dashboard["funnel"]
    assert funnel[1]["count"] == 2
    assert funnel[1]["denominator"] == 2
    assert funnel[2]["conversion_percent"] == 50.0


def test_dashboard_has_zero_weeks_and_timezone_aware_series() -> None:
    dashboard = build_dashboard(
        [MetricJob(1, at(3), ("remoteok",))],
        [
            MetricApplication(
                1,
                at(3),
                "interview",
                (MetricApplicationEvent("interview", at(10)),),
            )
        ],
        [],
        [],
        DashboardFilters(at(1, 0), at(22, 0), "America/Sao_Paulo"),
    )
    series = dashboard["series"]
    assert len(series) == 4
    assert sum(point["jobs"] for point in series) == 1
    assert sum(point["interviews"] for point in series) == 1


def test_dashboard_source_credit_is_first_origin_and_errors_are_counted() -> None:
    dashboard = build_dashboard(
        [MetricJob(1, at(1), ("remoteok", "other"))],
        [MetricApplication(1, at(2), "interview")],
        [MetricSearchRun("remoteok", at(2), "failed", error_message="timeout")],
        [MetricAgendaEvent("interview", at(20), None, "scheduled")],
        DashboardFilters(at(1, 0), at(22, 0)),
    )
    sources = dashboard["sources"]
    assert sources == [
        {
            "source_key": "remoteok",
            "jobs": 1,
            "applications": 1,
            "interviews": 1,
            "errors": 1,
            "application_rate_percent": 100.0,
        }
    ]
    assert dashboard["agenda"]["upcoming"] + dashboard["agenda"]["overdue"] == 1
