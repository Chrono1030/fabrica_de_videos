import pytest

from fabrica.economics import Scenario, VideoMetrics


def scenario(**changes):
    return Scenario(
        name="base",
        monthly_videos=30,
        eligible_views=100_000,
        assumed_rpm_usd=1,
        cost_per_video_usd=1,
        monthly_fixed_usd=10,
        human_hours=2,
        hourly_cost_usd=10,
        **changes,
    )


def test_no_income_without_both_eligibility_gates():
    data = scenario().calculate()
    assert data["estimated_revenue_usd"] == 0
    assert data["actual_revenue_usd"] is None
    assert data["break_even_views"] is None
    assert scenario(ypp_eligible=True).calculate()["estimated_revenue_usd"] == 0


def test_hypothetical_economic_arithmetic():
    data = scenario(ypp_eligible=True, monthly_shorts_eligible=True).calculate()
    assert data["estimated_monthly_cost_usd"] == 60
    assert data["estimated_revenue_usd"] == 100
    assert data["estimated_result_usd"] == 40
    assert data["break_even_views"] == 60_000
    assert data["estimated_margin_percent"] == 40
    assert data["kind"] == "hypothetical_scenario"


def test_revenue_source_and_bad_input():
    with pytest.raises(ValueError):
        scenario(ypp_eligible=True).model_validate(
            scenario().model_dump() | {"assumed_rpm_usd": -1}
        )
    with pytest.raises(ValueError, match="Ingreso real"):
        VideoMetrics(
            job_id="x",
            simulated=True,
            production_seconds=1,
            cpu_seconds=1,
            peak_rss_kib=1,
            artifact_bytes=1,
            actual_revenue_usd=100,
        )
