# Apex Zero-Human Grid — Orchestrator

**Version:** 1.0.0-breakthrough  
**Capability level:** Unprecedented autonomous product factory + revenue engine with human governance gates.

## What this is

A production-ready microservice that:

1. **Creates products** from a catalog of templates (mesh messenger, data monetization API, governance platform, trading bot).
2. **Scaffolds private GitHub repos** automatically and pushes starter code.
3. **Writes target MRR** into Postgres and tracks actual Stripe revenue.
4. **Runs a Quantum Revenue Engine** every 6 hours (observation + risk scoring only).
5. **Runs a 14-day Closed-Loop Optimizer** that *proposes* changes into a pending_approvals table.
6. **Never** makes a product public, changes pricing, or executes capital actions without an explicit human approval via the `/approvals` endpoint.

## Guardrails (non-negotiable)

- All products start `private`.
- Public launch requires governor approval.
- Pricing mutations require governor approval.
- Capital / trading actions are hard-blocked at the API level.
- Every action writes to an `audit_log` table with confidence score (RHNS-style).

## Quick start (after core stack is live)

```bash
# 1. Build & push image
cd orchestrator
docker build -t YOUR_ECR_OR_GHCR/apex-orchestrator:1.0.0-breakthrough .
docker push YOUR_ECR_OR_GHCR/apex-orchestrator:1.0.0-breakthrough

# 2. Update image name in k8s/*.yaml

# 3. Ensure secrets contain:
#    database-url, redis-url, github-token, stripe-secret-key
#    (and optionally openai/anthropic keys)

# 4. Deploy
cd ../scripts
chmod +x deploy.sh
./deploy.sh
```

## API surface

| Method | Path | Purpose |
|--------|------|---------|
| GET | /health | Liveness + engine status |
| POST | /products | Create private product from template |
| GET | /products | List all products |
| POST | /approvals | Human governor gate (make_public, apply_pricing) |
| GET | /revenue/summary | Latest MRR + risk scores |
| POST | /optimize/force | Manually trigger optimizer (still gated) |

## Revenue path

1. Create product → private + GitHub scaffold.
2. Revenue engine records actual vs target every 6 h.
3. When actual MRR crosses threshold, engine emits `PROPOSE_PUBLIC`.
4. You call `/approvals` with `action=make_public, approved=true`.
5. System marks public and (in full implementation) activates Stripe prices + frontend exposure.

This is the governed Zero-Human loop: autonomous creation and monitoring, human control on every external risk surface.
