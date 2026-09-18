"""
Apex Zero-Human Grid Orchestrator
Unprecedented capabilities:
- Autonomous product scaffolding from catalog templates
- GitHub repo creation + scaffolding push
- Target MRR injection into Postgres
- Stripe live revenue reconciliation
- 14-day closed-loop optimization with confidence gating
- Human approval gates on all external risk (public launch, pricing, capital)
- RHNS-style confidence + audit trail on every hop
- Self-healing via tenacity + health endpoints
"""

import asyncio
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from .config import settings
from .product_factory import ProductFactory
from .revenue_engine import QuantumRevenueEngine
from .optimizer import ClosedLoopOptimizer
from .github_manager import GitHubManager
from .db import get_db_pool, init_db
from .models import ProductCreate, ApprovalRequest, HealthResponse

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)
log = structlog.get_logger()

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("orchestrator_starting", version="1.0.0-breakthrough", env=settings.environment)
    await init_db()
    # Start background engines
    scheduler.add_job(
        run_revenue_engine,
        IntervalTrigger(hours=settings.revenue_engine_interval_hours),
        id="quantum_revenue_engine",
        replace_existing=True
    )
    scheduler.add_job(
        run_optimizer,
        CronTrigger(day=f"*/{settings.optimization_interval_days}"),
        id="closed_loop_optimizer",
        replace_existing=True
    )
    scheduler.start()
    log.info("scheduler_started")
    yield
    scheduler.shutdown()
    log.info("orchestrator_stopped")

app = FastAPI(
    title="Apex Zero-Human Grid Orchestrator",
    description="Autonomous product factory + revenue engine with human governance gates",
    version="1.0.0-breakthrough",
    lifespan=lifespan
)

# Global engines
factory = ProductFactory()
revenue_engine = QuantumRevenueEngine()
optimizer = ClosedLoopOptimizer()
github = GitHubManager()

async def run_revenue_engine():
    try:
        result = await revenue_engine.run_cycle()
        log.info("revenue_engine_cycle_complete", **result)
    except Exception as e:
        log.error("revenue_engine_failed", error=str(e))

async def run_optimizer():
    try:
        result = await optimizer.run_cycle()
        log.info("optimizer_cycle_complete", **result)
    except Exception as e:
        log.error("optimizer_failed", error=str(e))

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy",
        version="1.0.0-breakthrough",
        engines=["product_factory", "quantum_revenue", "closed_loop_optimizer"],
        guardrails_active=True
    )

@app.post("/products")
async def create_product(payload: ProductCreate, background_tasks: BackgroundTasks):
    """
    Create a new product from catalog template.
    Always starts PRIVATE. Public requires explicit approval.
    """
    log.info("product_create_requested", template=payload.template_id, name=payload.name)
    try:
        product = await factory.create(
            template_id=payload.template_id,
            name=payload.name,
            target_mrr=payload.target_mrr,
            metadata=payload.metadata or {}
        )
        background_tasks.add_task(factory.scaffold_github, product["id"])
        return {"status": "created_private", "product": product}
    except Exception as e:
        log.error("product_create_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/approvals")
async def submit_approval(payload: ApprovalRequest):
    """
    Human governor endpoint.
    Only after approval does the system mark product public,
    activate Stripe prices, or apply pricing changes.
    """
    log.info("approval_received", action=payload.action, resource_id=payload.resource_id, approved=payload.approved)
    if not payload.approved:
        return {"status": "rejected", "resource_id": payload.resource_id}
    
    if payload.action == "make_public":
        result = await factory.make_public(payload.resource_id)
        return {"status": "public_activated", "result": result}
    elif payload.action == "apply_pricing":
        result = await revenue_engine.apply_pricing(payload.resource_id, payload.params or {})
        return {"status": "pricing_applied", "result": result}
    elif payload.action == "capital_action":
        # Explicitly blocked without additional layers
        raise HTTPException(status_code=403, detail="Capital actions require multi-sig / higher gate")
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action {payload.action}")

@app.get("/products")
async def list_products():
    products = await factory.list_all()
    return {"products": products}

@app.get("/revenue/summary")
async def revenue_summary():
    summary = await revenue_engine.get_summary()
    return summary

@app.post("/optimize/force")
async def force_optimize():
    """Manual trigger for the 14-day loop (still gated on changes)."""
    result = await optimizer.run_cycle(force=True)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("orchestrator.main:app", host="0.0.0.0", port=8080, reload=False)
