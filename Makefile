.PHONY: dev dev-full mcp-start train-models test test-cov lint build deploy clean db-migrate kafka-topics

# ── Local Development ──────────────────────────────────────────────────────────
dev:
	cd backend && uvicorn main:app --reload --port 8000

dev-full:
	docker compose up --build

mcp-start:
	uvicorn backend.mcp_servers.bureau_mcp.server:app --port 9001 &
	uvicorn backend.mcp_servers.bank_txn_mcp.server:app --port 9002 &
	uvicorn backend.mcp_servers.gst_mcp.server:app --port 9003 &
	uvicorn backend.mcp_servers.rbi_compliance_mcp.server:app --port 9004 &
	uvicorn backend.mcp_servers.penny_drop_mcp.server:app --port 9005 &
	@echo "✅ All 5 MCP servers started"

frontend-dev:
	cd frontend && npm run dev

# ── Database ───────────────────────────────────────────────────────────────────
db-migrate:
	alembic upgrade head

db-rollback:
	alembic downgrade -1

db-reset:
	alembic downgrade base && alembic upgrade head

db-shell:
	psql $(DATABASE_URL)

# ── Kafka ──────────────────────────────────────────────────────────────────────
kafka-topics:
	docker compose exec kafka kafka-topics --create \
		--bootstrap-server localhost:9092 \
		--topic loan.documents.received \
		--partitions 6 --replication-factor 1 --if-not-exists
	docker compose exec kafka kafka-topics --create \
		--bootstrap-server localhost:9092 \
		--topic loan.decisions.completed \
		--partitions 6 --replication-factor 1 --if-not-exists
	@echo "✅ Kafka topics created"

# ── ML Models ─────────────────────────────────────────────────────────────────
train-credit:
	python backend/ml/credit_model/train.py
	@echo "✅ Credit model trained"

train-fraud:
	python backend/ml/fraud_model/train.py
	@echo "✅ Fraud model trained"

train-all: train-credit train-fraud
	@echo "✅ All models trained"

mlflow-ui:
	mlflow ui --port 5000 --host 0.0.0.0

# ── Testing ────────────────────────────────────────────────────────────────────
test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v \
		--cov=backend \
		--cov-report=html:htmlcov \
		--cov-report=term-missing \
		--cov-fail-under=70
	@echo "Coverage report: htmlcov/index.html"

test-agents:
	pytest tests/test_agents.py -v -s

test-ml:
	pytest tests/test_ml.py -v -s

test-mcp:
	pytest tests/test_mcp.py -v -s

test-api:
	pytest tests/test_api.py -v -s

# ── Code Quality ───────────────────────────────────────────────────────────────
lint:
	ruff check backend/ tests/
	mypy backend/ --ignore-missing-imports

format:
	ruff format backend/ tests/

security:
	bandit -r backend/ -ll

# ── Build & Deploy ─────────────────────────────────────────────────────────────
build:
	docker build -f infra/docker/backend.Dockerfile -t bfsi-backend:latest .
	docker build -f infra/docker/frontend.Dockerfile -t bfsi-frontend:latest ./frontend
	@echo "✅ Docker images built"

deploy-staging:
	kubectl set image deployment/bfsi-backend backend=bfsi-backend:$(IMAGE_TAG) -n bfsi-staging
	kubectl rollout status deployment/bfsi-backend -n bfsi-staging

terraform-plan:
	cd infra/terraform && terraform init && terraform plan

terraform-apply:
	cd infra/terraform && terraform apply -auto-approve

# ── Monitoring ─────────────────────────────────────────────────────────────────
logs:
	kubectl logs -f -l app=bfsi-backend -n bfsi-prod --tail=100

metrics:
	open http://localhost:9090  # Prometheus

grafana:
	open http://localhost:3001  # Grafana (admin/admin)

# ── Compliance ─────────────────────────────────────────────────────────────────
audit-report:
	python scripts/generate_audit_report.py

drift-check:
	python scripts/check_model_drift.py

# ── Cleanup ────────────────────────────────────────────────────────────────────
clean:
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache htmlcov .coverage
	@echo "✅ Cleaned"

help:
	@echo "BFSI Credit Intelligence — Available Commands:"
	@echo ""
	@echo "  Development:    make dev | dev-full | mcp-start | frontend-dev"
	@echo "  Database:       make db-migrate | db-rollback | db-reset"
	@echo "  Kafka:          make kafka-topics"
	@echo "  ML Models:      make train-all | train-credit | train-fraud | mlflow-ui"
	@echo "  Testing:        make test | test-cov | test-agents | test-ml | test-api"
	@echo "  Quality:        make lint | format | security"
	@echo "  Build/Deploy:   make build | deploy-staging | terraform-plan | terraform-apply"
	@echo "  Monitoring:     make logs | metrics | grafana"
	@echo "  Compliance:     make audit-report | drift-check"
