"""Escenarios explícitos, métricas operativas y resultados reales separados."""

import json
import math
from typing import Literal

from pydantic import Field, model_validator

from .metadata import Contract


class VideoMetrics(Contract):
    job_id: str
    simulated: bool
    production_seconds: float = Field(ge=0, allow_inf_nan=False)
    cpu_seconds: float = Field(ge=0, allow_inf_nan=False)
    peak_rss_kib: int = Field(ge=0)
    artifact_bytes: int = Field(ge=0)
    production_cost_usd: float = Field(default=0, ge=0, allow_inf_nan=False)
    api_calls: int = Field(default=0, ge=0)
    errors: int = Field(default=0, ge=0)
    retries: int = Field(default=0, ge=0)
    renderer: str | None = None
    render_wall_seconds: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    render_report_path: str | None = None
    storyboard_path: str | None = None
    human_hours: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    actual_revenue_usd: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    actual_revenue_source: str | None = None

    @model_validator(mode="after")
    def sourced_revenue(self):
        if self.actual_revenue_usd is not None and (
            self.simulated or not self.actual_revenue_source
        ):
            raise ValueError(
                "Ingreso real requiere fuente oficial y trabajo no simulado"
            )
        return self


class Scenario(Contract):
    name: Literal["pesimista", "base", "optimista"]
    monthly_videos: int = Field(ge=0)
    eligible_views: int = Field(ge=0)
    assumed_rpm_usd: float = Field(ge=0, allow_inf_nan=False)
    cost_per_video_usd: float = Field(ge=0, allow_inf_nan=False)
    monthly_fixed_usd: float = Field(ge=0, allow_inf_nan=False)
    human_hours: float = Field(ge=0, allow_inf_nan=False)
    hourly_cost_usd: float = Field(ge=0, allow_inf_nan=False)
    ypp_eligible: bool = False
    monthly_shorts_eligible: bool = False

    def calculate(self):
        cost = (
            self.monthly_videos * self.cost_per_video_usd
            + self.monthly_fixed_usd
            + self.human_hours * self.hourly_cost_usd
        )
        allowed = self.ypp_eligible and self.monthly_shorts_eligible
        revenue = self.eligible_views / 1000 * self.assumed_rpm_usd if allowed else 0
        return {
            "kind": "hypothetical_scenario",
            "name": self.name,
            "assumptions": self.model_dump(),
            "estimated_revenue_usd": revenue,
            "estimated_monthly_cost_usd": cost,
            "estimated_result_usd": revenue - cost,
            "estimated_margin_percent": (revenue - cost) / revenue * 100
            if revenue
            else None,
            "break_even_views": math.ceil(cost * 1000 / self.assumed_rpm_usd)
            if allowed and self.assumed_rpm_usd > 0
            else None,
            "actual_revenue_usd": None,
        }


def save_metrics(store, metrics):
    with store.connect() as db:
        db.execute(
            "INSERT INTO metrics VALUES(?,?) ON CONFLICT(job_id) DO UPDATE SET record=excluded.record",
            (metrics.job_id, metrics.model_dump_json()),
        )


def metrics_report(store):
    with store.connect() as db:
        records = [
            json.loads(r["record"]) for r in db.execute("SELECT record FROM metrics")
        ]
        completed = db.execute(
            "SELECT count(*) FROM calendar WHERE state='SIMULATED_DONE'"
        ).fetchone()[0]
        errors = db.execute(
            "SELECT count(*) FROM publication_events WHERE state IN "
            "('RETRY_WAIT','RECONCILE','BLOCKED_PERMISSION','BLOCKED_PERMANENT','QUARANTINED')"
        ).fetchone()[0]
    return {
        "videos_recorded": len(records),
        "simulated_cycles_completed": completed,
        "publication_errors_recorded": errors,
        "records": records,
        "recorded_cost_usd": sum(r["production_cost_usd"] for r in records),
        "recorded_human_hours": sum(
            r["human_hours"] for r in records if r["human_hours"] is not None
        )
        if any(r["human_hours"] is not None for r in records)
        else None,
        "actual_revenue_usd": sum(
            r["actual_revenue_usd"]
            for r in records
            if r["actual_revenue_usd"] is not None
        )
        if any(r["actual_revenue_usd"] is not None for r in records)
        else None,
    }
