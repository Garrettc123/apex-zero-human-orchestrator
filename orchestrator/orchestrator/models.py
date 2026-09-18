from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class ProductCreate(BaseModel):
    template_id: str = Field(..., description="ID from PRODUCT_CATALOG.yaml")
    name: str
    target_mrr: float = 5000.0
    metadata: Optional[Dict[str, Any]] = None

class ApprovalRequest(BaseModel):
    action: str  # make_public | apply_pricing | capital_action
    resource_id: str
    approved: bool
    params: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    approver: Optional[str] = "governor"

class HealthResponse(BaseModel):
    status: str
    version: str
    engines: List[str]
    guardrails_active: bool

class Product(BaseModel):
    id: str
    name: str
    template_id: str
    status: str  # private | pending_public | public | deprecated
    target_mrr: float
    actual_mrr: float = 0.0
    github_repo: Optional[str] = None
    stripe_product_id: Optional[str] = None
    created_at: datetime
    metadata: Dict[str, Any] = {}

class RevenueSnapshot(BaseModel):
    product_id: str
    actual_mrr: float
    target_mrr: float
    variance_pct: float
    risk_score: float
    recommendation: str
    timestamp: datetime
