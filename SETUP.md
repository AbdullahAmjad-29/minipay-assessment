# Setup

## Requirements
CentOS/RHEL-family VM, Docker, Minikube (docker driver), Python 3.12, PostgreSQL 16.

## Database
    sudo dnf install -y postgresql-server postgresql-contrib
    sudo postgresql-setup --initdb
    sudo systemctl enable --now postgresql
    # create DB/user, set pg_hba.conf to md5 for minipay_app, GRANT ALL ON SCHEMA public
    psql -U minipay_app -d minipay -f database/schema.sql
    python3 database/generate_data.py > database/seed.sql
    psql -U minipay_app -d minipay -f database/seed.sql

## App
    cd app && python3 -m venv ../venv && source ../venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env   # fill in real DB_PASSWORD, API_KEY
    uvicorn app.main:app --host 0.0.0.0 --port 8000

## Docker
    docker build -t minipay-api:latest .
    # requires host.docker.internal + Postgres listen_addresses='*' + pg_hba.conf rule
    # for docker bridge subnet - see investigation/docker-postgres-connectivity.md

## Kubernetes (Minikube)
    minikube start --driver=docker --memory=2200 --cpus=2
    minikube image load minipay-api:latest
    kubectl apply -f kubernetes/01-postgres-config.yaml
    kubectl apply -f kubernetes/02-postgres-statefulset.yaml
    kubectl apply -f kubernetes/03-api-deployment.yaml
    curl http://$(minikube ip):30080/health

## Python support tool
    cd python && pip install -r requirements.txt
    python3 support_tool.py --transaction TXN00000029
    python3 -m pytest tests/ -v

## Tests
    python3 -m pytest tests/api/ -v
    playwright install chromium   # CentOS: also needs nss/nspr/atk/etc via dnf, see notes below
    python3 -m pytest tests/ui/ --base-url http://127.0.0.1:8000 -v

Note: Playwright's --with-deps only supports apt-based distros. On CentOS/RHEL, install manually:
    sudo dnf install -y nss nspr atk at-spi2-atk at-spi2-core cups-libs libdrm libxkbcommon mesa-libgbm alsa-lib libX11 libXcomposite libXdamage libXext libXfixes libXrandr libxcb pango cairo
