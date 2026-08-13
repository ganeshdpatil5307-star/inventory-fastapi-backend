# Inventory Management API — FastAPI Backend

Production-ready REST API for an Inventory Management System. Built to exercise a
PaaS **App Platform** end to end: GitHub integration, build & deploy, auto-deploy on
push, environment variables, managed PostgreSQL connectivity, health checks and
monitoring.

Pairs with the Nuxt 3 frontend in **`inventory-nuxt-frontend`**.

---

## Features

| Area | What's included |
|---|---|
| **Auth** | JWT (HS256) — register, JSON login, OAuth2 password flow for Swagger, `/auth/me` |
| **Products** | Full CRUD, unique SKU, price/reorder level, category + supplier relations |
| **Categories** | Full CRUD, duplicate-name protection, delete guarded by product usage |
| **Suppliers** | Full CRUD, contact details, delete guarded by product usage |
| **Inventory** | Stock In, Stock Out (rejects overdraw), Stock Adjust, full movement ledger |
| **Dashboard** | Counts, inventory value, low/out-of-stock, category breakdown, recent movements |
| **Search** | `?q=` free-text search on every list endpoint + filters (category, supplier, low stock, price range) |
| **Pagination** | `?page=&size=` on every list endpoint, with `meta` (total, pages, has_next/has_prev) |
| **Sorting** | `?sort=&order=` with whitelisted columns |
| **Validation** | Pydantic v2 models, constrained fields, uniform 422 error envelope |
| **Health check** | `/api/v1/health` (verifies DB with `SELECT 1`, returns 503 when down), `/api/v1/health/live` |
| **Swagger** | `/docs` (Swagger UI), `/redoc`, `/openapi.json` |
| **CORS** | Origin allow-list from `BACKEND_CORS_ORIGINS` |
| **Monitoring** | Structured request logs + `X-Process-Time` response header |

---

## Tech stack

FastAPI · SQLAlchemy 2.0 · Pydantic v2 · PostgreSQL (psycopg2) · python-jose · passlib/bcrypt · Gunicorn + Uvicorn workers

---

## Project structure

```
app/
├── main.py                  # App factory, CORS, middleware, exception handlers
├── core/
│   ├── config.py            # Settings from env; DATABASE_URL normalisation
│   └── security.py          # Password hashing + JWT create/decode
├── db/
│   ├── session.py           # Engine + SessionLocal + Base + get_db()
│   ├── base.py              # Model registry for metadata
│   └── init_db.py           # Table creation + first-admin seed
├── models/                  # User, Category, Supplier, Product, StockMovement
├── schemas/                 # Pydantic request/response models
├── services/pagination.py   # Reusable offset pagination
└── api/
    ├── deps.py              # DB session, current user/admin, pagination deps
    └── v1/
        ├── router.py        # Router aggregation
        └── endpoints/       # auth, users, categories, suppliers,
                             # products, inventory, dashboard, health
scripts/seed_demo_data.py    # Optional demo dataset
.do/app.yaml                 # App Platform spec (existing DB binding)
Dockerfile · Procfile · requirements.txt · runtime.txt · .env.example
```

---

## Database — uses your EXISTING database

This app **never creates a database and never hardcodes credentials.** It reads a
single environment variable:

```
DATABASE_URL=postgresql://user:pass@host:25060/dbname
```

On startup `app/core/config.py` normalises whatever the platform hands over:

* `postgres://…` and `postgresql://…` → `postgresql+psycopg2://…` (required by SQLAlchemy 2.x)
* appends `sslmode=require` when `DB_SSL_REQUIRE=true` (managed Postgres needs TLS)

On App Platform, bind it to the database you already have rather than typing a value:

```yaml
- key: DATABASE_URL
  value: ${your-existing-db.DATABASE_URL}
```

Tables are created on first boot when `AUTO_CREATE_TABLES=true`. Switch it to
`false` and adopt Alembic once your schema stabilises.

---

## Environment variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `DATABASE_URL` | ✅ | — | Bind to your existing managed Postgres |
| `DB_SSL_REQUIRE` | | `false` | Set `true` for managed cloud Postgres |
| `SECRET_KEY` | ✅ | dev key | `openssl rand -hex 32`. Mark as SECRET |
| `ALGORITHM` | | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | | `60` | Token lifetime |
| `BACKEND_CORS_ORIGINS` | ✅ | empty (`*`) | Comma-separated frontend origins |
| `API_V1_PREFIX` | | `/api/v1` | Route prefix |
| `ENVIRONMENT` | | `production` | Shown in `/health` |
| `DEBUG` / `LOG_LEVEL` | | `false` / `INFO` | Logging |
| `AUTO_CREATE_TABLES` | | `true` | Create tables on boot |
| `SEED_ADMIN` | | `true` | Seed first admin when the users table is empty |
| `FIRST_ADMIN_EMAIL` | | `admin@example.com` | Seed admin login |
| `FIRST_ADMIN_PASSWORD` | | `ChangeMe123!` | **Mark as SECRET and change it** |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` / `DB_POOL_RECYCLE` | | `5` / `10` / `1800` | Connection pool tuning |
| `PORT` | | platform-set | Bound by the start command |

---

## Local development

```bash
git clone https://github.com/<your-username>/inventory-fastapi-backend.git
cd inventory-fastapi-backend

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # then edit DATABASE_URL + SECRET_KEY

uvicorn app.main:app --reload --port 8000
```

* Swagger UI → <http://localhost:8000/docs>
* Health → <http://localhost:8000/api/v1/health>

Optional demo data:

```bash
python -m scripts.seed_demo_data
```

Docker:

```bash
docker build -t inventory-api .
docker run -p 8080:8080 --env-file .env inventory-api
```

---

## Deploying to App Platform

### Build & run commands

| Setting | Value |
|---|---|
| **Environment** | Python 3.11 |
| **Build command** | `pip install --no-cache-dir -r requirements.txt` |
| **Run command** | `gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:$PORT --timeout 120` |
| **HTTP port** | `8080` (or whatever the platform injects as `$PORT`) |
| **Health check path** | `/api/v1/health` |

### Steps

1. **Create the app** → *Create App* → **GitHub** → authorise → pick
   `inventory-fastapi-backend`, branch `main`.
2. **Enable auto-deploy** — tick *Autodeploy on push*. Every push to `main`
   triggers a new build and rolling deploy.
3. **Attach your existing database** — in *Resources*, add the managed Postgres
   database you already have. Do **not** create a new one.
4. **Set environment variables** (App-level or component-level):
   * `DATABASE_URL` → `${<your-db-name>.DATABASE_URL}`
   * `DB_SSL_REQUIRE` → `true`
   * `SECRET_KEY` → generated value, type **SECRET**
   * `BACKEND_CORS_ORIGINS` → your deployed frontend URL
   * `FIRST_ADMIN_EMAIL` / `FIRST_ADMIN_PASSWORD` (SECRET)
5. **Set the health check** to `/api/v1/health` with a ~20s initial delay so the
   first migration/bootstrap can finish.
6. **Deploy**, then verify:

```bash
curl https://<your-api-domain>/api/v1/health
curl https://<your-api-domain>/docs
```

A spec file is committed at [`.do/app.yaml`](.do/app.yaml) if your platform
supports importing an app spec — edit the repo, cluster and secret placeholders first.

### If your database is IP-restricted

Add your app to the database's trusted sources/firewall, otherwise `/api/v1/health`
will return `503` with `"database": {"connected": false}` — which is exactly how
you can tell connectivity from application faults.

---

## API reference

Base path: `/api/v1`

### Auth
| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | Create a user |
| POST | `/auth/login` | JSON login → JWT (used by the frontend) |
| POST | `/auth/login/token` | OAuth2 form login (Swagger *Authorize*) |
| GET | `/auth/me` | Current user |

### Catalogue
| Method | Path | Description |
|---|---|---|
| GET | `/products` | List — `q`, `category_id`, `supplier_id`, `low_stock`, `min_price`, `max_price`, `sort`, `order`, `page`, `size` |
| POST/GET/PUT/DELETE | `/products{/id}` | CRUD |
| GET | `/categories` · `/categories/all` | Paginated list · dropdown list |
| POST/GET/PUT/DELETE | `/categories{/id}` | CRUD |
| GET | `/suppliers` · `/suppliers/all` | Paginated list · dropdown list |
| POST/GET/PUT/DELETE | `/suppliers{/id}` | CRUD |

### Inventory
| Method | Path | Description |
|---|---|---|
| GET | `/inventory/movements` | Ledger — `q`, `product_id`, `movement_type`, pagination |
| POST | `/inventory/stock-in` | Receive stock |
| POST | `/inventory/stock-out` | Issue stock (422 if insufficient) |
| POST | `/inventory/adjust` | Set absolute counted quantity |

### Dashboard, users, health
| Method | Path | Description |
|---|---|---|
| GET | `/dashboard/summary` | KPIs, low stock, recent movements, category breakdown |
| GET | `/users` | List users (admin only) |
| PATCH/DELETE | `/users/{id}…` | Activate/deactivate, delete (admin only) |
| GET | `/health` | Liveness + DB readiness |
| GET | `/health/live` | Liveness only |

### Paginated response shape

```json
{
  "items": [ ... ],
  "meta": { "page": 1, "size": 20, "total": 42, "pages": 3,
            "has_next": true, "has_prev": false }
}
```

### Quick smoke test

```bash
API=https://<your-api-domain>

TOKEN=$(curl -s -X POST $API/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"ChangeMe123!"}' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -s $API/api/v1/dashboard/summary -H "Authorization: Bearer $TOKEN"
curl -s "$API/api/v1/products?q=mouse&page=1&size=10" -H "Authorization: Bearer $TOKEN"
```

---

## Monitoring

* `/api/v1/health` — returns `503` when the database is unreachable, so the
  platform's health check fails loudly instead of serving a broken app.
* `X-Process-Time` header on every response for latency spot-checks.
* Structured stdout logs (health probes excluded) — picked up by the platform's
  log viewer/runtime logs.

---

## Security notes

* Passwords hashed with bcrypt; never returned by any endpoint.
* All business endpoints require `Authorization: Bearer <token>`.
* Secrets come only from environment variables — `.env` is git-ignored.
* Change `FIRST_ADMIN_PASSWORD` immediately after the first deploy, or set
  `SEED_ADMIN=false` and create the first user via `/auth/register`.

## License

MIT
