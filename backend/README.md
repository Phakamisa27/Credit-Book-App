# Credit Book — backend

Python 3.12 · FastAPI · PostgreSQL · SQLAlchemy 2.0 · Alembic · Pydantic ·
JWT + bcrypt.

The project README (one level up) covers installation, environment variables,
the database schema and the business rules. This file is the short version for
working in here.

- **[API.md](API.md)** — every endpoint: method, URL, auth, request, response, errors.
- **[../MIGRATION.md](../MIGRATION.md)** — the Express → FastAPI migration record.
- **`/api/docs`** — interactive docs, while the server is running.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows;  source .venv/bin/activate elsewhere
pip install -r requirements.txt

cp .env.example .env              # then fill in DATABASE_URL and JWT_SECRET

python -m app.db.create_database  # create the database
alembic upgrade head              # create the tables   (existing DB: alembic stamp 0001)
python -m app.db.seed             # development data — never against real books

python run.py                     # http://localhost:5000
pytest                            # the test suite
```

## Layout

```text
app/
├── main.py            FastAPI app: CORS, body limit, security headers,
│                      exception handlers, the /api router, the static frontend
├── api/
│   ├── router.py      everything under /api
│   └── routes/        one module per resource — parse and validate the request,
│                      call a service, wrap the result in the response envelope
├── services/          business rules (balances, the overpayment rule, the
│                      server-side grand total, derived status and urgency)
├── repositories/      all SQL, including the aggregate report statements
├── models/            SQLAlchemy ORM, one file per table
├── schemas/           Pydantic request models + the {success, data} envelope
├── dependencies/      get_current_user_id — the JWT gate on every protected route
├── core/
│   ├── config.py      reads backend/.env, fails fast on a missing secret
│   ├── security.py    bcrypt hashing, JWT sign/verify
│   ├── errors.py      ApiError and the handlers that turn anything else into
│   │                  a logged 500 and a one-sentence message
│   ├── money.py       Decimal arithmetic; float only at the JSON boundary
│   ├── validate.py    the user-facing validation messages
│   └── serialize.py   UTC ISO timestamps and plain YYYY-MM-DD dates
└── db/                engine/session, create_database, seed
```

The layering is one-way: `route → service → repository → database`. A route
never writes SQL, and a repository never decides a business rule.

## Conventions

- **Money is `Decimal` everywhere**, converted to a JSON number once, at the
  response boundary. Never `float` in a calculation.
- **Every query filters by `user_id`** taken from the verified token, so one
  account can never read or write another's rows.
- **A transaction and its item rows are written in one database transaction**,
  holding `SELECT … FOR UPDATE` on the customer. Partial writes cannot happen,
  and two simultaneous payments cannot both pass the overpayment check.
- **Errors the owner should see** are raised as `ApiError`. Anything else is a
  bug: logged in full, and answered with
  "Something went wrong. Please try again."
- **The response envelope is part of the contract** — `{success, data}` or
  `{success, message}`, on every route, including 404s under `/api`.
