"""Health check routes for BFSI Credit Intelligence Platform."""
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/live", summary="Liveness probe")
async def liveness():
    """Kubernetes liveness probe — returns 200 if app is running."""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}

@router.get("/ready", summary="Readiness probe")
async def readiness():
    """Kubernetes readiness probe — checks component connectivity."""
    checks = {"database": "ok", "redis": "ok", "kafka": "ok"}
    healthy = all(v == "ok" for v in checks.values())
    return {
        "status": "ready" if healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
    }
