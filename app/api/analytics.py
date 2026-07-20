"""
Analytics API - Aggregate data for charts and insights.
"""
import logging
from fastapi import APIRouter

from app.config.database import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)


@router.get("/overview")
def get_overview():
    """Single call for dashboard stat cards."""
    try:
        db = get_supabase()

        companies = db.table("companies").select("id").execute()
        total_companies = len(companies.data) if companies.data else 0

        sessions = db.table("interview_sessions").select("id, status, final_score, started_at").execute()
        rows = sessions.data if sessions.data else []

        total_sessions = len(rows)
        active_sessions = len([r for r in rows if r.get("status") in ("active", "in_progress")])
        completed_sessions = len([r for r in rows if r.get("status") == "completed"])
        scores = [float(r["final_score"]) for r in rows if r.get("final_score") is not None]
        avg_score = round(sum(scores) / len(scores), 2) if scores else None
        completion_rate = round(completed_sessions / total_sessions * 100, 1) if total_sessions > 0 else 0

        return {
            "total_companies": total_companies,
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "completed_sessions": completed_sessions,
            "average_score": avg_score,
            "completion_rate": completion_rate,
        }
    except Exception as e:
        logger.error(f"Analytics overview error: {e}")
        return {
            "total_companies": 0,
            "total_sessions": 0,
            "active_sessions": 0,
            "completed_sessions": 0,
            "average_score": None,
            "completion_rate": 0,
        }


@router.get("/scores/trend")
def get_scores_trend():
    """Score trend over time (grouped by day)."""
    try:
        db = get_supabase()
        result = (
            db.table("interview_sessions")
            .select("started_at, final_score")
            .not_.is_("final_score", "null")
            .order("started_at", desc=False)
            .execute()
        )
        rows = result.data if result.data else []

        # Group by date
        daily = {}
        for r in rows:
            date_str = r["started_at"][:10] if r.get("started_at") else None
            if not date_str:
                continue
            if date_str not in daily:
                daily[date_str] = []
            daily[date_str].append(float(r["final_score"]))

        trend = [
            {"date": d, "avg_score": round(sum(s) / len(s), 2), "count": len(s)}
            for d, s in sorted(daily.items())
        ]
        return trend
    except Exception as e:
        logger.error(f"Scores trend error: {e}")
        return []


@router.get("/scores/distribution")
def get_scores_distribution():
    """Histogram of score ranges."""
    try:
        db = get_supabase()
        result = (
            db.table("interview_sessions")
            .select("final_score")
            .not_.is_("final_score", "null")
            .execute()
        )
        rows = result.data if result.data else []

        ranges = [
            {"range": "0-2", "min": 0, "max": 2, "count": 0},
            {"range": "3-4", "min": 3, "max": 4, "count": 0},
            {"range": "5-6", "min": 5, "max": 6, "count": 0},
            {"range": "7-8", "min": 7, "max": 8, "count": 0},
            {"range": "9-10", "min": 9, "max": 10, "count": 0},
        ]

        for r in rows:
            score = float(r["final_score"])
            for bucket in ranges:
                if bucket["min"] <= score <= bucket["max"]:
                    bucket["count"] += 1
                    break

        return [{"range": b["range"], "count": b["count"]} for b in ranges]
    except Exception as e:
        logger.error(f"Scores distribution error: {e}")
        return []


@router.get("/sessions/by-company")
def get_sessions_by_company():
    """Sessions count per company."""
    try:
        db = get_supabase()
        companies = db.table("companies").select("id, name").execute()
        company_map = {c["id"]: c["name"] for c in (companies.data or [])}

        sessions = db.table("interview_sessions").select("company_id, final_score").execute()
        rows = sessions.data if sessions.data else []

        grouped = {}
        for r in rows:
            cid = r.get("company_id")
            if cid not in grouped:
                grouped[cid] = {"scores": [], "count": 0}
            grouped[cid]["count"] += 1
            if r.get("final_score") is not None:
                grouped[cid]["scores"].append(float(r["final_score"]))

        result = []
        for cid, data in grouped.items():
            scores = data["scores"]
            result.append({
                "company_id": cid,
                "name": company_map.get(cid, f"Company {cid}"),
                "session_count": data["count"],
                "avg_score": round(sum(scores) / len(scores), 2) if scores else None,
            })

        result.sort(key=lambda x: x["session_count"], reverse=True)
        return result
    except Exception as e:
        logger.error(f"Sessions by company error: {e}")
        return []


@router.get("/sessions/by-role")
def get_sessions_by_role():
    """Sessions grouped by job role."""
    try:
        db = get_supabase()
        result = (
            db.table("interview_sessions")
            .select("job_role, final_score")
            .execute()
        )
        rows = result.data if result.data else []

        grouped = {}
        for r in rows:
            role = r.get("job_role", "Unknown")
            if role not in grouped:
                grouped[role] = {"scores": [], "count": 0}
            grouped[role]["count"] += 1
            if r.get("final_score") is not None:
                grouped[role]["scores"].append(float(r["final_score"]))

        result = []
        for role, data in grouped.items():
            scores = data["scores"]
            result.append({
                "job_role": role,
                "count": data["count"],
                "avg_score": round(sum(scores) / len(scores), 2) if scores else None,
            })

        result.sort(key=lambda x: x["count"], reverse=True)
        return result
    except Exception as e:
        logger.error(f"Sessions by role error: {e}")
        return []
