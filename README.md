# BFSI Credit Intelligence — Agentic Loan Underwriting Platform

> **Production-grade agentic AI platform for real-time loan underwriting in Indian BFSI sector.**
> Built with LangGraph v0.3, MCP (Model Context Protocol), XGBoost + SHAP, and RBI-compliance guardrails.

---

## What This Does

An end-to-end loan underwriting system that replaces a 3-5 day manual process with a **< 5 second AI decision**:

1. Applicant submits loan application with documents
2. OCR pipeline extracts data (English + Hindi via Surya OCR)
3. 6 specialized LangGraph agents run in parallel:
   - **Document Validator** → verifies KYC documents, OCR extraction
   - **Financial Analyst** → income, obligations, DTI ratio
   - **Credit Scorer** → XGBoost model + CIBIL bureau (parallel)
   - **Fraud Detector** → Isolation Forest + rule engine (parallel)
   - **Compliance Checker** → RBI Master Directions, DPDP Act 2023
   - **Decision Agent** → final underwriting decision
4. SHAP values explain every decision (regulator-ready)
5. Decision published to Kafka → audit log → PostgreSQL

---

## Architecture

```
┌─────────────┐    ┌──────────────────────────────────────────────────┐
│   Next.js   │    │              LangGraph StateGraph                │
│  Dashboard  │───▶│                                                  │
│  Port 3000  │    │  [Doc Validator] → [Financial Analyst]           │
└─────────────┘    │         ↙                    ↘                   │
                   │  [Credit Scorer]    [Fraud Detector]  ← parallel │
       FastAPI     │         ↘                    ↙                   │
       Port 8000   │  [Compliance Checker] → [Decision Agent]         │
          │        │         interrupt_before=["decision_agent"]      │
          │        └──────────────────────────────────────────────────┘
          │
   ┌──────┴──────┐    ┌─────────────────────────────────────────┐
   │ MCP Servers │    │           Infrastructure                │
   │ Bureau 9001 │    │  PostgreSQL 16  │  Redis 7              │
   │ BankTxn9002 │    │  Kafka (MSK)   │  MLflow               │
   │  GST   9003 │    │  Qdrant Vector │  Evidently Monitoring  │
   │  RBI   9004 │    │  Airflow DAGs  │  Prometheus + Grafana  │
   │ PennyDp9005 │    └─────────────────────────────────────────┘
   └─────────────┘
```

---

## Key Technical Stack

| Layer | Technology |
|-------|-----------|
| Agent Orchestration | LangGraph v0.3 (StateGraph, parallel fan-out, human-in-loop) |
| LLM | Claude Sonnet (Anthropic) via LangChain |
| MCP Servers | FastMCP + Streamable HTTP transport (5 servers) |
| Credit Model | XGBoost + Optuna HPO + SMOTE + SHAP |
| Fraud Detection | Isolation Forest + rule engine |
| OCR | PyMuPDF + Surya OCR (Hindi + English) |
| Streaming | Apache Kafka (Confluent) |
| API | FastAPI (async) |
| Frontend | Next.js 14 App Router + Tailwind |
| MLOps | MLflow + Evidently + Airflow (weekly retrain) |
| Infra | EKS (ap-south-1) + Terraform + GitHub Actions |
| Compliance | RBI Master Directions, DPDP Act 2023, PMLA 2002 |

---

## Quick Start

```bash
# Clone and setup
cd ~/Desktop/bfsi-credit-intelligence
cp .env.example .env
# Fill in your ANTHROPIC_API_KEY

# Start everything
make dev-full          # Docker Compose: all services
make kafka-topics      # Create required Kafka topics
make train-all         # Train credit + fraud ML models

# Or run backend only
pip install -r requirements.txt
make mcp-start         # Start all 5 MCP servers
make dev               # Start FastAPI on :8000
cd frontend && npm install && npm run dev   # Next.js on :3000
```

---

## MCP Servers

| Server | Port | Tools | Purpose |
|--------|------|-------|---------|
| `bureau_mcp` | 9001 | `fetch_bureau_score`, `fetch_bureau_report_details` | CIBIL/Experian credit bureau data |
| `bank_txn_mcp` | 9002 | `fetch_bank_statement`, `detect_obligations` | AA Framework — account aggregation |
| `gst_mcp` | 9003 | `verify_gstin`, `fetch_gst_returns` | MSME/business loan GST verification |
| `rbi_compliance_mcp` | 9004 | `check_rbi_compliance`, `get_fair_lending_guidelines` | RBI Master Directions validator |
| `penny_drop_mcp` | 9005 | `verify_pan`, `verify_bank_account`, `verify_aadhaar_otp`, `check_ckyc` | KYC identity verification |

---

## Agentic Flow Detail

```python
# Parallel fan-out after Financial Analyst
graph.add_edge("financial_analyst", "credit_scorer")
graph.add_edge("financial_analyst", "fraud_detector")

# Human-in-the-loop before final decision
graph.compile(interrupt_before=["decision_agent"])

# Auto-reject gates
def route_post_compliance(state):
    if state.fraud_risk_score > 0.85:
        return "auto_reject"
    if "CRITICAL" in state.compliance_flags:
        return "auto_reject"
    return "decision_agent"
```

---

## ML Models

### Credit Scoring
- **Features**: 11 engineered features (credit score, bureau score, DTI, bank balance, income stability, loan-to-income ratio, fraud risk)
- **Model**: XGBoost with Optuna 50-trial hyperparameter optimization
- **Class Imbalance**: SMOTE oversampling (default rate ~5%)
- **Explainability**: SHAP TreeExplainer — every decision has feature attributions
- **MLflow**: Experiment tracking + model registry + deployment gating (AUC quality gate)

### Fraud Detection
- **Model**: Isolation Forest (anomaly detection — no labelled fraud data required)
- **Rule Engine**: Income-bank ratio, DTI > 60%, loan > 5× annual income
- **Combined Score**: `min(1.0, rules_score + ml_score × 0.4)`

### Drift Monitoring
- **Evidently AI**: Weekly drift reports on credit features
- **Airflow DAG**: Auto-retrain on drift detection with AUC quality gate

---

## RBI Compliance

| Rule | Implementation |
|------|---------------|
| DTI ≤ 50% | Automated check in `compliance_checker.py` |
| KYC mandatory | Penny drop + Aadhaar OTP + PAN verification |
| PMLA ₹2L threshold | Automated suspicious transaction flag |
| Age eligibility | Min 18, max varies by loan type |
| Fair lending | No discrimination on caste/religion/gender |
| DPDP Act 2023 | PII masked in logs, consent tracked, 180-day retention |
| Audit trail | Immutable audit log in PostgreSQL, S3 backup |
| SHAP explanation | Regulator-ready decision explanation for every loan |

---

## API Reference

### `POST /api/v1/loans/underwrite`
```json
{
  "applicant_name": "Ajay Mahale",
  "pan_number": "ABCPM1234A",
  "loan_type": "personal",
  "loan_amount": 500000,
  "tenure_months": 36,
  "monthly_income": 80000,
  "account_number": "123456789012",
  "ifsc_code": "HDFC0001234"
}
```

**Response:**
```json
{
  "application_id": "APP-20260501-001",
  "decision": "APPROVED",
  "approved_amount": 500000,
  "interest_rate": 11.5,
  "credit_score": 0.78,
  "risk_tier": "NEAR_PRIME",
  "fraud_risk_score": 0.08,
  "shap_values": { "credit_score": 0.15, "dti_ratio": -0.04, ... },
  "decision_explanation": "Application approved. Strong income stability...",
  "rbi_compliant": true,
  "processing_time_ms": 2840
}
```

---

## Running Tests

```bash
make test          # All tests
make test-agents   # Agent unit tests
make test-ml       # ML model tests
make test-mcp      # MCP server tests
make test-cov      # With coverage report (target: 70%+)
```

---

## Deployment

```bash
# Terraform (AWS Mumbai ap-south-1)
cd infra/terraform
terraform init
terraform plan
terraform apply    # Creates: EKS, RDS, ElastiCache, MSK Kafka, S3 (KMS encrypted)

# CI/CD: GitHub Actions on push to main
# → Tests → Security scan (Trivy) → Build ECR image → Deploy to EKS
```

---

## Resume Bullet Points 🚀

Use these in your Naukri / LinkedIn profile:

- **Architected** production agentic AI underwriting platform using LangGraph v0.3 with 6 parallel agents, reducing loan decision time from 3 days to under 5 seconds
- **Built** 5 MCP (Model Context Protocol) servers for real-time bureau, GST, Account Aggregator, and KYC integrations using FastMCP + Streamable HTTP transport
- **Implemented** XGBoost credit scoring model with SHAP explainability, Optuna HPO, and SMOTE class balancing; deployed via MLflow model registry with AUC quality gates
- **Engineered** DPDP Act 2023 and RBI Master Direction compliance layer with automated DTI, KYC, and PMLA checks; full audit trail in PostgreSQL
- **Deployed** on AWS EKS (Mumbai) with Terraform, MSK Kafka, encrypted RDS multi-AZ, and GitHub Actions CI/CD including Trivy security scanning
- **Integrated** Surya OCR for Hindi + English document extraction, Evidently AI for model drift monitoring, and Airflow for weekly automated model retraining

---

## Folder Structure

```
bfsi-credit-intelligence/
├── backend/
│   ├── agents/          # 6 LangGraph agents
│   ├── ml/              # XGBoost, Isolation Forest, SHAP
│   ├── mcp_servers/     # 5 MCP servers (Bureau, BankTxn, GST, RBI, PennyDrop)
│   ├── document_processing/  # OCR pipeline (PyMuPDF + Surya)
│   ├── streaming/       # Kafka producer + consumer
│   └── main.py          # FastAPI app
├── frontend/            # Next.js 14 underwriter dashboard
├── mlops/airflow/       # Weekly model retrain DAGs
├── infra/
│   ├── k8s/             # EKS manifests + HPA
│   ├── terraform/       # AWS infrastructure (ap-south-1)
│   └── docker/          # Multi-stage Dockerfiles
├── tests/               # pytest suite (agents, ML, MCP, API)
├── docker-compose.yml   # Full local stack
└── Makefile             # All dev commands
```
