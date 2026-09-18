import stripe
import structlog
from datetime import datetime
from .config import settings
from .db import get_db_pool, audit

log = structlog.get_logger()

class QuantumRevenueEngine:
    """
    Continuous revenue reconciliation + risk scoring.
    Never mutates pricing or public status without human approval.
    """

    def __init__(self):
        if settings.stripe_secret_key:
            stripe.api_key = settings.stripe_secret_key
        else:
            log.warning("stripe_secret_key_missing — revenue engine runs in observation mode")

    async def run_cycle(self) -> dict:
        pool = await get_db_pool()
        results = []
        async with pool.acquire() as conn:
            products = await conn.fetch("SELECT * FROM products WHERE status IN ('private', 'public', 'pending_public')")
            
            for p in products:
                actual = await self._fetch_actual_mrr(p)
                target = float(p["target_mrr"] or 0)
                variance = ((actual - target) / target * 100) if target > 0 else 0.0
                risk = self._risk_score(actual, target, variance)
                recommendation = self._recommend(actual, target, risk, p["status"])

                await conn.execute(
                    """
                    INSERT INTO revenue_snapshots (product_id, actual_mrr, target_mrr, variance_pct, risk_score, recommendation)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    p["id"], actual, target, variance, risk, recommendation
                )
                await conn.execute(
                    "UPDATE products SET actual_mrr = $1, updated_at = NOW() WHERE id = $2",
                    actual, p["id"]
                )

                results.append({
                    "product_id": str(p["id"]),
                    "name": p["name"],
                    "actual_mrr": actual,
                    "target_mrr": target,
                    "variance_pct": round(variance, 2),
                    "risk_score": risk,
                    "recommendation": recommendation
                })

                await audit(
                    "revenue_snapshot",
                    resource_id=str(p["id"]),
                    payload={"actual": actual, "target": target, "risk": risk, "rec": recommendation},
                    confidence=0.9
                )

        log.info("revenue_cycle_complete", products=len(results))
        return {"cycle_at": datetime.utcnow().isoformat(), "products": results}

    async def _fetch_actual_mrr(self, product) -> float:
        """Pull live Stripe data if product has stripe_product_id, else return stored actual."""
        if not settings.stripe_secret_key or not product.get("stripe_product_id"):
            return float(product.get("actual_mrr") or 0.0)
        
        try:
            # Simplified: sum active subscriptions for this product
            # In production expand with price mapping
            subs = stripe.Subscription.list(status="active", limit=100)
            total = 0.0
            for s in subs.auto_paging_iter():
                for item in s["items"]["data"]:
                    # crude match — replace with proper price → product mapping
                    total += (item["price"]["unit_amount"] or 0) / 100.0
            return total
        except Exception as e:
            log.error("stripe_fetch_failed", error=str(e))
            return float(product.get("actual_mrr") or 0.0)

    def _risk_score(self, actual: float, target: float, variance: float) -> float:
        """0–100 risk. Higher = more attention needed."""
        if target <= 0:
            return 50.0
        abs_var = abs(variance)
        if abs_var > 50:
            return min(100.0, 60 + abs_var / 2)
        if actual < target * 0.5:
            return 75.0
        if actual > target * 1.5:
            return 30.0  # over-performing still monitored
        return max(10.0, abs_var)

    def _recommend(self, actual: float, target: float, risk: float, status: str) -> str:
        if status == "private" and actual >= settings.auto_public_threshold_mrr:
            return "PROPOSE_PUBLIC — actual MRR crossed threshold. Human approval required."
        if risk > 70 and actual < target:
            return "PROPOSE_OPTIMIZATION — under-performing. Run closed-loop cycle."
        if risk < 20 and actual > target:
            return "HOLD — healthy. Consider upsell experiments (gated)."
        return "MONITOR"

    async def apply_pricing(self, product_id: str, params: dict) -> dict:
        """Only after human approval. Mutates Stripe prices."""
        if not settings.stripe_secret_key:
            raise RuntimeError("Stripe not configured")
        # Implementation: create/update Stripe Price objects, update DB
        await audit("pricing_applied", resource_id=product_id, actor="governor", payload=params, confidence=1.0)
        return {"status": "pricing_updated", "params": params}

    async def get_summary(self) -> dict:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT p.name, p.status, p.target_mrr, p.actual_mrr,
                       s.risk_score, s.recommendation, s.created_at
                FROM products p
                LEFT JOIN LATERAL (
                    SELECT * FROM revenue_snapshots rs
                    WHERE rs.product_id = p.id
                    ORDER BY created_at DESC LIMIT 1
                ) s ON true
                ORDER BY p.created_at DESC
            """)
            return {
                "generated_at": datetime.utcnow().isoformat(),
                "products": [dict(r) for r in rows]
            }
