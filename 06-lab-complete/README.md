# Lab 12 - Production Agent Complete

Project nay dap ung checklist final project:
- REST API tra loi cau hoi (`POST /ask`)
- Luu conversation history trong Redis (stateless app)
- API key auth (`X-API-Key`)
- Rate limit 10 req/phut/user
- Cost guard 10 USD/thang/user
- Health (`GET /health`) va Readiness (`GET /ready`)
- Graceful shutdown (SIGTERM)
- Structured JSON logging
- Docker multi-stage + Nginx load balancing + Redis
- San sang deploy Railway hoac Render

## Cau truc

```text
06-lab-complete/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── auth.py
│   ├── rate_limiter.py
│   └── cost_guard.py
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
├── .env.example
├── railway.toml
├── render.yaml
└── check_production_ready.py
```

## Chay local voi Docker

```bash
cd 06-lab-complete
cp .env.example .env
docker compose up --build --scale agent=3
```

Test nhanh:

```bash
curl http://localhost:18080/health
curl http://localhost:18080/ready
curl -X POST http://localhost:18080/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: secret" \
  -H "X-User-Id: user1" \
  -d '{"question":"Hello production agent"}'
```

## Kiem thu rate limit va budget

Rate limit (lan thu 11 trong 1 phut se tra 429):

```bash
for i in $(seq 1 11); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST http://localhost:18080/ask \
    -H "Content-Type: application/json" \
    -H "X-API-Key: secret" \
    -H "X-User-Id: user-rate" \
    -d '{"question":"test"}'
done
```

Cost guard (doi trong `.env`: `MONTHLY_BUDGET_USD=0.02`, moi request ton 0.01):

```bash
docker compose down
docker compose up --build --scale agent=3
```

Sau 2 request se nhan `402`.

## Kiem tra checklist tu dong

```bash
python check_production_ready.py
```

## Deploy Railway

```bash
railway login
railway init
railway variables set REDIS_URL=redis://<your-redis-url>
railway variables set AGENT_API_KEY=<your-secret-key>
railway variables set RATE_LIMIT_PER_MINUTE=10
railway variables set MONTHLY_BUDGET_USD=10
railway up
```

## Deploy Render

1. Push repo len GitHub
2. Tao Redis service tren Render de lay `REDIS_URL`
3. Render -> New -> Blueprint -> chon repo
4. Set env vars: `REDIS_URL`, `AGENT_API_KEY`
5. Deploy va test public URL:

```bash
curl https://<your-render-url>/health
```
