 MiniPay – Implementation & L2 Support Engineer Assessment

MiniPay is a small payment-processing app (FastAPI + PostgreSQL + minimal HTML/JS UI), built and operated end-to-end for this assessment: deployed to Docker and Kubernetes (Minikube), investigated via SQL, automated via Python/pytest/Playwright, with 3 real incidents diagnosed and fixed.

See ARCHITECTURE.md for design decisions, SETUP.md to reproduce the environment, AI_USAGE.md for AI usage.

See ARCHITECTURE.md for design decisions, SETUP.md to reproduce the environment, AI_USAGE.md for AI usage.

## Structure
- `app/` - FastAPI API + static UI
- `database/` - schema, data generator, migrations
- `kubernetes/` - manifests (Postgres StatefulSet, API Deployment, broken/fixed incident manifests)
- `sql/` - 7 required investigation queries + PERFORMANCE.md
- `python/` - L2 support CLI + unit tests
- `tests/api/`, `tests/ui/` - pytest + Playwright suites
- `investigation/` - INCIDENT-001/002/003 RCAs, Docker/K8s debugging writeups
- `evidence/` - Linux and Rancher evidence

## Status
Complete. All required tasks and 3 incidents done; see investigation/ for RCAs.

