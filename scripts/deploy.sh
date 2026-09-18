#!/usr/bin/env bash
set -euo pipefail

echo "=== Apex Zero-Human Grid — Deploy Orchestrator ==="
echo "This script assumes:"
echo "  1. You have already run the PLANTING_GUIDE core stack (EKS, RDS, secrets)"
echo "  2. You have built and pushed the orchestrator image to YOUR_ECR_OR_GHCR"
echo "  3. kubectl is pointed at apex-ai-cluster"
echo ""

NAMESPACE=apex-ai-production

# Ensure namespace exists
kubectl get ns $NAMESPACE >/dev/null 2>&1 || kubectl create namespace $NAMESPACE

# Apply manifests
echo "Applying orchestrator deployment + service + catalog ConfigMap..."
kubectl apply -f ../k8s/orchestrator-deployment.yaml

echo "Applying revenue + optimizer CronJobs..."
kubectl apply -f ../k8s/revenue-cronjob.yaml

echo "Waiting for rollout..."
kubectl rollout status deployment/apex-orchestrator -n $NAMESPACE --timeout=180s

echo ""
echo "=== Live ==="
kubectl get pods -n $NAMESPACE -l app=apex-orchestrator
kubectl get svc -n $NAMESPACE apex-orchestrator
kubectl get cronjobs -n $NAMESPACE

echo ""
echo "Health check (port-forward if needed):"
echo "  kubectl port-forward -n $NAMESPACE svc/apex-orchestrator 8080:80"
echo "  curl http://localhost:8080/health"
echo ""
echo "Create first product:"
echo "  curl -X POST http://localhost:8080/products \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"template_id\":\"mesh_messenger\",\"name\":\"Mesh Alpha\",\"target_mrr\":8000}'"
echo ""
echo "All products start PRIVATE. Use /approvals endpoint to promote to public after review."
