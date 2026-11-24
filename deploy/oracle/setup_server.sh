#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# One-time setup of an Ubuntu 24.04 server (Oracle Cloud ARM or any x86 VM)
# for Enterprise AI OS: PostgreSQL, Redis, Qdrant, Neo4j, Python 3.11.7,
# the backend service, the website build and Nginx.
#
# Run from the project folder, AFTER creating backend/.env:
#     bash deploy/oracle/setup_server.sh <postgres-major-version>
# Example (laptop runs PostgreSQL 17):
#     bash deploy/oracle/setup_server.sh 17
#
# It is safe to run again: finished steps are skipped or repeated harmlessly.
# ---------------------------------------------------------------------------
set -euo pipefail

PG_VERSION="${1:-}"
if [[ -z "$PG_VERSION" ]]; then
  echo "Give the PostgreSQL major version of your laptop, e.g.: bash deploy/oracle/setup_server.sh 17"
  exit 1
fi

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND="$APP_DIR/backend"
FRONTEND="$APP_DIR/frontend/frontend"
APP_USER="$(id -un)"
PYTHON_VERSION="3.11.7"
QDRANT_VERSION="v1.20.2"
export DEBIAN_FRONTEND=noninteractive

step() { echo; echo "==> $*"; }

[[ -f "$BACKEND/.env" ]] || { echo "backend/.env is missing. Create it first (see the guide, step 6)."; exit 1; }

env_value() {  # value of KEY in backend/.env (last occurrence, quotes removed)
  grep -E "^$1=" "$BACKEND/.env" | tail -1 | cut -d= -f2- | sed -e 's/^["'\'']//' -e 's/["'\'']$//' || true
}

# PostgreSQL user, password and database name come from DATABASE_URL in backend/.env
read -r PG_USER PG_PASS PG_DB < <(python3 - "$(env_value DATABASE_URL)" <<'PY'
import sys
from urllib.parse import urlparse, unquote
u = urlparse(sys.argv[1])
print(unquote(u.username or "postgres"), unquote(u.password or ""), (u.path or "/enterprise_ai_os").lstrip("/"))
PY
)
NEO4J_PASS="$(env_value NEO4J_PASSWORD)"
REDIS_PASS="$(env_value REDIS_PASSWORD)"
[[ -n "$PG_PASS" ]] || { echo "DATABASE_URL in backend/.env has no password."; exit 1; }
if [[ ${#NEO4J_PASS} -lt 8 ]]; then echo "NEO4J_PASSWORD in backend/.env must have at least 8 characters."; exit 1; fi

step "System packages"
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install -y curl git build-essential ca-certificates gnupg nginx redis-server \
  nodejs npm certbot python3-certbot-nginx iptables-persistent

step "PostgreSQL $PG_VERSION (official PostgreSQL repository)"
sudo apt-get install -y postgresql-common
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y
sudo apt-get install -y "postgresql-$PG_VERSION"
sudo systemctl enable --now postgresql
sudo -u postgres psql -v ON_ERROR_STOP=1 -q -c "ALTER USER \"$PG_USER\" WITH PASSWORD '${PG_PASS//\'/\'\'}';" 2>/dev/null \
  || sudo -u postgres psql -v ON_ERROR_STOP=1 -q -c "CREATE USER \"$PG_USER\" WITH SUPERUSER PASSWORD '${PG_PASS//\'/\'\'}';"
if ! sudo -u postgres psql -Atq -c "SELECT 1 FROM pg_database WHERE datname='$PG_DB'" | grep -q 1; then
  sudo -u postgres createdb -O "$PG_USER" "$PG_DB"
fi

step "Redis (only reachable from this server)"
if [[ -n "$REDIS_PASS" ]]; then
  sudo sed -i -E 's/^#? *requirepass .*/requirepass '"$REDIS_PASS"'/' /etc/redis/redis.conf
  grep -q "^requirepass " /etc/redis/redis.conf || echo "requirepass $REDIS_PASS" | sudo tee -a /etc/redis/redis.conf >/dev/null
fi
sudo systemctl enable --now redis-server
sudo systemctl restart redis-server

step "Neo4j (official Neo4j repository)"
if [[ ! -f /etc/apt/sources.list.d/neo4j.list ]]; then
  curl -fsSL https://debian.neo4j.com/neotechnology.gpg.key | sudo gpg --dearmor --yes -o /usr/share/keyrings/neo4j.gpg
  echo "deb [signed-by=/usr/share/keyrings/neo4j.gpg] https://debian.neo4j.com stable latest" | sudo tee /etc/apt/sources.list.d/neo4j.list >/dev/null
  sudo apt-get update -y
fi
sudo apt-get install -y neo4j
CONF=/etc/neo4j/neo4j.conf
for setting in "server.memory.heap.initial_size=1g" "server.memory.heap.max_size=1g" "server.memory.pagecache.size=512m"; do
  key="${setting%%=*}"
  sudo sed -i "/^#\?${key//./\\.}=/d" "$CONF"
  echo "$setting" | sudo tee -a "$CONF" >/dev/null
done
sudo systemctl stop neo4j || true
# Sets the password only when Neo4j has never been started with a password before
sudo -u neo4j neo4j-admin dbms set-initial-password "$NEO4J_PASS" 2>/dev/null || true
sudo systemctl enable --now neo4j

step "Qdrant $QDRANT_VERSION"
case "$(uname -m)" in
  aarch64|arm64) QDRANT_FILE="qdrant-aarch64-unknown-linux-musl.tar.gz" ;;
  x86_64)        QDRANT_FILE="qdrant-x86_64-unknown-linux-gnu.tar.gz" ;;
  *) echo "Unsupported processor: $(uname -m)"; exit 1 ;;
esac
if [[ ! -x /opt/qdrant/qdrant ]]; then
  tmp="$(mktemp -d)"
  curl -fsSL -o "$tmp/qdrant.tgz" "https://github.com/qdrant/qdrant/releases/download/$QDRANT_VERSION/$QDRANT_FILE"
  tar -xzf "$tmp/qdrant.tgz" -C "$tmp"
  sudo install -D -m 755 "$tmp/qdrant" /opt/qdrant/qdrant
  rm -rf "$tmp"
fi
id qdrant >/dev/null 2>&1 || sudo useradd --system --home /var/lib/qdrant --shell /usr/sbin/nologin qdrant
sudo mkdir -p /var/lib/qdrant/storage /var/lib/qdrant/snapshots
sudo chown -R qdrant:qdrant /var/lib/qdrant
sudo install -m 644 "$APP_DIR/deploy/oracle/qdrant.service" /etc/systemd/system/qdrant.service

step "Python $PYTHON_VERSION and backend packages"
if ! command -v uv >/dev/null 2>&1 && [[ ! -x "$HOME/.local/bin/uv" ]]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
UV="$(command -v uv || echo "$HOME/.local/bin/uv")"
"$UV" python install "$PYTHON_VERSION"
[[ -x "$BACKEND/.venv/bin/python" ]] || "$UV" venv --seed -p "$PYTHON_VERSION" "$BACKEND/.venv"
PIP="$BACKEND/.venv/bin/python -m pip"
$PIP install --upgrade pip
# CPU-only PyTorch first: the default Linux download adds several GB of NVIDIA GPU libraries
TORCH_PIN="$(grep -E '^torch==' "$BACKEND/requirements.txt" | head -1)"
$PIP install "${TORCH_PIN:-torch}" --index-url https://download.pytorch.org/whl/cpu
$PIP install -r "$BACKEND/requirements.txt"
"$BACKEND/.venv/bin/python" --version

step "Website build"
( cd "$FRONTEND" && npm ci && npm run build )

step "Backend service"
sed -e "s#__APP_DIR__#$APP_DIR#g" -e "s#__APP_USER__#$APP_USER#g" "$APP_DIR/deploy/oracle/enterprise-ai.service" \
  | sudo tee /etc/systemd/system/enterprise-ai.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now qdrant
sudo systemctl enable enterprise-ai

step "Nginx (public address -> backend)"
sudo install -m 644 "$APP_DIR/deploy/oracle/nginx-enterprise-ai.conf" /etc/nginx/sites-available/enterprise-ai
sudo ln -sf /etc/nginx/sites-available/enterprise-ai /etc/nginx/sites-enabled/enterprise-ai
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx

step "Server firewall: allow web traffic (ports 80 and 443)"
for port in 80 443; do
  if ! sudo iptables -C INPUT -p tcp --dport "$port" -m state --state NEW -j ACCEPT 2>/dev/null; then
    reject_line="$(sudo iptables -L INPUT --line-numbers -n | awk '$2=="REJECT"{print $1; exit}')"
    if [[ -n "$reject_line" ]]; then
      sudo iptables -I INPUT "$reject_line" -p tcp --dport "$port" -m state --state NEW -j ACCEPT
    else
      sudo iptables -A INPUT -p tcp --dport "$port" -m state --state NEW -j ACCEPT
    fi
  fi
done
sudo netfilter-persistent save

step "Status"
for svc in postgresql redis-server neo4j qdrant nginx; do
  printf "  %-14s %s\n" "$svc" "$(systemctl is-active "$svc" || true)"
done
cat <<MSG

Setup finished. Next (see the guide):
  1. Copy your PostgreSQL backup to this server and restore it (step 9).
  2. Start the backend:   sudo systemctl start enterprise-ai
  3. Open http://<your server's public IP>/ in a browser.
MSG
