import asyncpg
import structlog
from .config import settings

log = structlog.get_logger()
_pool = None

async def init_db():
    global _pool
    _pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
    async with _pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name TEXT NOT NULL,
                template_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'private',
                target_mrr NUMERIC(12,2) NOT NULL DEFAULT 0,
                actual_mrr NUMERIC(12,2) NOT NULL DEFAULT 0,
                github_repo TEXT,
                stripe_product_id TEXT,
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS revenue_snapshots (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                product_id UUID REFERENCES products(id),
                actual_mrr NUMERIC(12,2),
                target_mrr NUMERIC(12,2),
                variance_pct NUMERIC(8,2),
                risk_score NUMERIC(5,2),
                recommendation TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                event_type TEXT NOT NULL,
                resource_id TEXT,
                actor TEXT DEFAULT 'system',
                payload JSONB,
                confidence NUMERIC(5,4),
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS pending_approvals (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                action TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                payload JSONB,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                resolved_at TIMESTAMPTZ
            );
        """)
    log.info("db_initialized")

async def get_db_pool():
    if _pool is None:
        await init_db()
    return _pool

async def audit(event_type: str, resource_id: str = None, actor: str = "system", payload: dict = None, confidence: float = 1.0):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO audit_log (event_type, resource_id, actor, payload, confidence) VALUES ($1, $2, $3, $4, $5)",
            event_type, resource_id, actor, payload or {}, confidence
        )
