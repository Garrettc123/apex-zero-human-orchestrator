import structlog
from datetime import datetime
from .config import settings
from .db import get_db_pool, audit

log = structlog.get_logger()

class ClosedLoopOptimizer:
    """
    14-day closed-loop: measure → learn → optimize → deploy (gated).
    Never auto-applies public or pricing changes.
    Writes proposed config into pending_approvals for human review.
    """

    async def run_cycle(self, force: bool = False) -> dict:
        pool = await get_db_pool()
        proposals = []

        async with pool.acquire() as conn:
            products = await conn.fetch("""
                SELECT p.*, s.actual_mrr, s.variance_pct, s.risk_score, s.recommendation
                FROM products p
                LEFT JOIN LATERAL (
                    SELECT * FROM revenue_snapshots rs
                    WHERE rs.product_id = p.id
                    ORDER BY created_at DESC LIMIT 1
                ) s ON true
            """)

            for p in products:
                if p["risk_score"] and float(p["risk_score"]) > 60:
                    proposal = {
                        "product_id": str(p["id"]),
                        "name": p["name"],
                        "action": "optimize_parameters",
                        "rationale": p["recommendation"] or "High risk score",
                        "suggested_changes": {
                            "outreach_intensity": "increase" if float(p.get("actual_mrr") or 0) < float(p["target_mrr"] or 1) else "hold",
                            "pricing_experiment": False,  # always gated
                            "feature_flags": {}
                        },
                        "confidence": 0.72
                    }
                    await conn.execute(
                        """
                        INSERT INTO pending_approvals (action, resource_id, payload, status)
                        VALUES ('optimize_parameters', $1, $2, 'pending')
                        """,
                        str(p["id"]), proposal
                    )
                    proposals.append(proposal)
                    await audit(
                        "optimization_proposed",
                        resource_id=str(p["id"]),
                        payload=proposal,
                        confidence=0.72
                    )

        log.info("optimizer_cycle_complete", proposals=len(proposals), force=force)
        return {
            "cycle_at": datetime.utcnow().isoformat(),
            "proposals_created": len(proposals),
            "proposals": proposals,
            "note": "All proposals require human approval before any deployment"
        }
