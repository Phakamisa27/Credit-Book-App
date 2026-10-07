# ThathaCash — Your shop, your control

A cash-flow and stock app for South African spaza shop owners, built as a
**validation MVP** on top of the original Credit Book app.

It answers four questions for the owner:

1. How much cash do I have? *(Cash available — the one number on Home)*
2. How much of it can I safely take? *(Safe to draw — cash, minus what is kept for restocking, minus an emergency buffer; see `backend/app/services/shop_rules.py`)*
3. What is running low? *(Stock)*
4. What money came in and went out, and how much did I take for myself? *(Transactions, Draws)*

**Home shows one number and one action.** Cash available, the "Safe to draw"
expander, one line if stock is running low, and a Log money button. Everything
else is reachable from the menu, not stacked on Home. On a first visit the
owner sees only "Count your cash", then the result — nothing else.

## ThathaCash at a glance

| Screen | Page | Script | API |
|---|---|---|---|
| Home | `dashboard.html` | `js/home.js` | `GET /api/home` |
| Stock | `stock.html` | `js/stock.js` | `GET/POST /api/items`, `PATCH /api/items/:id` |
| ~~Create order~~ (parked) | `order.html` | `js/order.js` | `GET /api/order` |
| Transactions | `transactions.html` | `js/money.js` | `GET/POST /api/cash`, `DELETE /api/cash/:id` |
| Draws | `draws.html` | `js/draws.js` | `GET /api/cash?type=DRAW` |
| More | `settings.html` | `js/settings.js` | `/api/auth/me` |

- **Parked:** the recommended order + WhatsApp sharing screen is built and
  works, but is deliberately out of the MVP. Nothing links to it; it opens at
  `/order.html` and its `GET /api/order` endpoint is untouched. Delete it or
  link it from Stock whenever you want it back.
- The "log money" form is shared by every screen: `frontend/js/cash-entry.js`.
- ThathaCash styles: `frontend/css/thathacash.css` (colour tokens stay in `base.css`).
- **Every business rule** (the 70/30 split, "running low", order totals) is in
  one file: `backend/app/services/shop_rules.py`.
- Database: migration `0002` adds `quantity`, `low_stock_level` and
  `reorder_quantity` to `items`, and a new `cash_entries` table. It only adds;
  no Credit Book table or row is changed.

The Credit Book features below (customers, credit, reminders, reports) still
work, and their pages still open by URL. They are simply no longer in the menu.

---

# Credit Book (the foundation)

A digital credit book for a small business owner. It replaces the paper notebook
used to track who bought on credit, how much they owe, and when they promised to
pay.

Built for one person's daily use — not as a demo. That shapes every decision in
here: no multi-tenancy, no microservices, no build step, and balances that are
always calculated from the ledger rather than stored and hoped for.

---

## What it does

- Add, edit, search and delete customers
- Record credit covering **several items at once** — item, quantity, unit price,
  line total and a running grand total — as one transaction
- Record payments received
- Calculate each customer's outstanding balance automatically
- Flag accounts that are owing, paid up, or overdue
- Keep a full transaction history per customer, with a running balance
- Capture a customer signature and a product photo when giving credit
- Set payment reminders and send them via WhatsApp or SMS (English or isiZulu)
- Show a dashboard and reports: outstanding, overdue, top debtors, daily activity
- Quick-entry items (Bread R18.50, Airtime R30) for faster capture

---

## Technology

| Layer | Choice |
|---|---|
| Frontend | HTML5, CSS3, vanilla JavaScript, Fetch API |
| Backend | Python 3.12, FastAPI |
| Database | PostgreSQL, SQLAlchemy 2.0, Alembic |
| Validation | Pydantic |
| Auth | JWT (PyJWT) + bcrypt password hashing |
| Tests | pytest + FastAPI TestClient |

No frontend framework, no bundler, no TypeScript. Open a page and it runs.

The backend was migrated from Node.js/Express to Python/FastAPI without
changing the database, the API contract or a single line of the frontend. See
[MIGRATION.md](MIGRATION.md) for what moved where.

---

## Folder structure

```text
credit-book-app/
│
├── frontend/                  Static files, served by the backend
│   ├── css/                   base.css owns the design tokens; shell.css the layout
│   ├── js/
│   │   ├── api.js             The only place that calls the backend
│   │   ├── app.js             Shared helpers, navigation shell, login guard
│   │   ├── auth.js            Login / register / landing
│   │   ├── modal.js           Small dialog helper
│   │   ├── dashboard.js
│   │   ├── customers.js       List, add, edit, profile
│   │   ├── transactions.js    Record credit + transactions feed
│   │   ├── reminders.js
│   │   ├── reports.js
│   │   └── settings.js
│   ├── index.html             Landing
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── customers.html
│   ├── customer-profile.html
│   ├── add-customer.html
│   ├── edit-customer.html
│   ├── record-credit.html
│   ├── transactions.html
│   ├── reminders.html
│   ├── reports.html
│   └── settings.html
│
├── backend/
│   ├── app/
│   │   ├── main.py            FastAPI app: middleware, error handlers, static frontend
│   │   ├── api/routes/        URL → handler (auth, customers, transactions,
│   │   │                      reminders, reports, items, health)
│   │   ├── services/          Business rules
│   │   ├── repositories/      All SQL
│   │   ├── models/            SQLAlchemy ORM, one file per table
│   │   ├── schemas/           Pydantic request models + the response envelope
│   │   ├── dependencies/      get_current_user_id (JWT)
│   │   ├── core/              config, security, errors, money, validate, serialize
│   │   └── db/                engine/session, create_database, seed
│   ├── alembic/               Migrations (0001 = the current schema)
│   ├── tests/                 pytest + TestClient
│   ├── run.py                 Entry point
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── API.md                 Full endpoint reference
│   ├── .env.example
│   └── .env                   Yours — git-ignored, never committed
│
├── MIGRATION.md               Express → FastAPI migration record
├── README.md
└── .gitignore
```

---

## Installation

Requires **Python 3.11+** and **PostgreSQL 14+**.

```bash
cd backend
python -m venv .venv
```

Activate it, then install:

```bash
# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Environment variables

Copy the example and fill it in:

```bash
cp backend/.env.example backend/.env
```

```env
PORT=5000
NODE_ENV=development
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/credit_book
JWT_SECRET=a_long_random_string
JWT_EXPIRES_IN=30d
CORS_ORIGIN=*
JSON_BODY_LIMIT=8mb
```

Generate a real secret:

```bash
python -c "import secrets; print(secrets.token_hex(48))"
```

`backend/.env` is git-ignored. Never commit it.

---

## Database setup

From `backend/`, with the virtualenv active:

```bash
python -m app.db.create_database   # create the database named in DATABASE_URL
alembic upgrade head               # create the tables
python -m app.db.seed              # load development test data
```

The first two read `DATABASE_URL` from your `.env`, so you never type the
password twice and you do not need `psql` on your PATH.

| Command | What it does |
|---|---|
| `python -m app.db.create_database` | Create the database named in `DATABASE_URL`, if missing |
| `alembic upgrade head` | Apply every migration |
| `alembic downgrade -1` | Undo the last migration |
| `alembic current` | Which revision this database is at |
| `alembic revision --autogenerate -m "…"` | Draft a migration from model changes |
| `python -m app.db.seed` | Load development test data |

**Upgrading an existing Credit Book database**, one that already has its tables
from before the migration: do not run `upgrade`, which would try to create them
again. Record the schema as already present instead:

```bash
alembic stamp 0001
```

### Test login — development only

`python -m app.db.seed` creates this account. **Delete it before real use.**

```text
Email:    owner@creditbook.test
Password: Password123
```

It comes with 6 customers, 14 transactions, reminders and quick items.

---

## Running the app

One command runs everything — FastAPI serves the API *and* the frontend:

```bash
cd backend
python run.py
```

Then open **http://localhost:5000**.

Interactive API documentation is at **http://localhost:5000/api/docs**.

`run.py` checks PostgreSQL is reachable before starting, and reloads on file
changes outside production. To run uvicorn directly:

```bash
uvicorn app.main:app --reload --port 5000
```

### Running the frontend separately (optional)

You do not need to, but if you prefer a separate static server (VS Code Live
Server on port 5500, say), `frontend/js/api.js` detects it and points at
`http://localhost:5000/api`. Set `CORS_ORIGIN=http://localhost:5500` in `.env`.

---

## Development commands

| Command | What it does |
|---|---|
| `python run.py` | Run the server (auto-reload outside production) |
| `uvicorn app.main:app --reload` | Run uvicorn directly |
| `pytest` | Run the API test suite |
| `pytest tests/test_multi_item.py -v` | Run one file, verbosely |
| `python -m app.db.create_database` | Create the database named in `DATABASE_URL` |
| `alembic upgrade head` | Apply migrations |
| `python -m app.db.seed` | Load development test data |

`pytest` needs a running PostgreSQL. Each test module uses its own throwaway
account and deletes it afterwards, so it will not touch your books.

---

## Database schema

Six tables. Money is always `NUMERIC(12,2)` — never a float.

**users** — the owner. The business profile lives here rather than in its own
table, because there is exactly one owner.

| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| full_name | TEXT NOT NULL | |
| email | TEXT NOT NULL UNIQUE | login identity |
| password_hash | TEXT NOT NULL | bcrypt, 10 rounds |
| business_name, business_phone, profile_image | TEXT | profile |
| created_at, updated_at | TIMESTAMPTZ | |

**customers**

| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| user_id | FK → users, CASCADE | |
| full_name | TEXT NOT NULL | |
| phone | TEXT NOT NULL | unique per user |
| email, address, gender, notes | TEXT | optional |
| created_at, updated_at | TIMESTAMPTZ | |

**transactions** — the ledger.

| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| user_id, customer_id | FK, CASCADE | |
| type | TEXT | `CREDIT` or `PAYMENT` |
| amount | NUMERIC(12,2) | must be > 0 |
| description | TEXT NOT NULL | |
| due_date | DATE | credit only |
| notes, signature, product_photo | TEXT | signature/photo are data URIs |
| created_at | TIMESTAMPTZ | |

**transaction_items** — the line items of a credit. Bread, milk and airtime
taken in one visit are ONE transaction with three item rows.

| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| transaction_id | FK → transactions, CASCADE | |
| name | TEXT NOT NULL | |
| quantity | INTEGER | must be > 0 |
| unit_price | NUMERIC(12,2) | must be > 0 |
| line_total | NUMERIC(12,2) | `CHECK (line_total = quantity * unit_price)` |
| position | INTEGER | preserves the order they were entered |

The parent transaction stays the ledger entry: its `amount` is the grand total,
so every balance and report query keeps aggregating `transactions` alone and
never has to know these rows exist.

Quantity is an **integer**. Whole units keep `line_total = quantity ×
unit_price` exact to the cent, with no rounding to argue about later. To sell
1.5 kg, enter quantity 1 with the unit price for that weight.

**reminders**

| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| user_id, customer_id | FK, CASCADE | |
| amount | NUMERIC(12,2) | |
| due_date | DATE NOT NULL | |
| status | TEXT | `PENDING` / `SENT` / `DONE` / `CANCELLED` |
| notes | TEXT | |

**items** — quick-entry products, unique per user by name.

### There is no `balance` column

A customer's balance is derived on every read:

```sql
SUM(CASE WHEN type = 'CREDIT' THEN amount ELSE -amount END)
```

A stored balance can drift away from the transactions that produced it. A
derived one cannot. At this data volume the query costs nothing.

Status is derived the same way:

- `PAID` — balance is zero or less
- `OVERDUE` — money is owed and the earliest due date has passed
- `OWING` — money is owed, nothing is late yet

---

## API overview

Full per-endpoint reference — request body, response body and every error —
is in [backend/API.md](backend/API.md), and interactively at `/api/docs` while
the server is running. The summary:

All responses share one shape:

```json
{ "success": true, "data": {} }
```

```json
{ "success": false, "message": "Customer not found." }
```

Every route except the auth ones needs `Authorization: Bearer <token>`.

### Auth

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/auth/status` | Does an account exist yet? |
| POST | `/api/auth/register` | Create the owner account |
| POST | `/api/auth/login` | Get a token |
| POST | `/api/auth/logout` | Client discards its token |
| GET | `/api/auth/me` | Current account + business profile |
| PATCH | `/api/auth/me` | Update profile |
| POST | `/api/auth/change-password` | Change password |

### Customers

| Method | Path |
|---|---|
| GET | `/api/customers?search=&status=` |
| GET | `/api/customers/:id` |
| POST | `/api/customers` |
| PUT / PATCH | `/api/customers/:id` |
| DELETE | `/api/customers/:id` |
| GET | `/api/customers/:id/transactions` |
| POST | `/api/customers/:id/transactions` |

`search` matches name or phone (digits typed without spaces still match).
`status` is `OWING`, `PAID`, `OVERDUE` or `ALL`.

### Transactions

| Method | Path |
|---|---|
| GET | `/api/transactions?type=&from=&to=&limit=` |
| GET | `/api/transactions/:id` |
| DELETE | `/api/transactions/:id` |

### Reminders

| Method | Path |
|---|---|
| GET | `/api/reminders?status=&customerId=` |
| POST | `/api/reminders` |
| PUT / PATCH | `/api/reminders/:id` |
| DELETE | `/api/reminders/:id` |

### Reports

| Method | Path |
|---|---|
| GET | `/api/reports/summary` |
| GET | `/api/reports/dashboard` |
| GET | `/api/reports?days=30` |

### Items

| Method | Path |
|---|---|
| GET | `/api/items` |
| POST | `/api/items` |
| DELETE | `/api/items/:id` |

---

## Business rules

**A credit can cover several products.** `POST /api/customers/:id/transactions`
takes either shape:

```jsonc
// Multi-item: the server computes the grand total from the lines.
{
  "type": "CREDIT",
  "dueDate": "2026-09-01",
  "items": [
    { "name": "Bread",   "quantity": 2, "unitPrice": 15 },
    { "name": "Perfume", "quantity": 1, "unitPrice": 120 },
    { "name": "Milk",    "quantity": 3, "unitPrice": 18 },
    { "name": "Airtime", "quantity": 1, "unitPrice": 50 }
  ]
}
// -> one transaction of R254.00; the balance moves once, by R254.00.

// Single amount: for payments, or a credit captured in a hurry.
{ "type": "PAYMENT", "amount": 200, "description": "Cash payment" }
```

**The grand total is always computed server-side** from the line items. An
`amount` sent alongside `items` is ignored, not trusted — so the books cannot
be talked into disagreeing with the items that produced them. The arithmetic of
each line is enforced by the database too, via a `CHECK` constraint.

**A payment may not exceed the balance owed.** If a customer owes R1,000 and you
try to record R1,200, the API rejects it and tells you the actual balance. The
book tracks debt, not deposits — a negative balance would be a typo, not a real
state. The check runs inside a database transaction holding a row lock on the
customer, so two payments submitted at the same instant cannot both slip through.

**Deleting a transaction is allowed.** Amounts get mistyped. Because the balance
is derived, removing the row is all it takes to correct the books.

**Deleting a customer removes their transactions and reminders** (`ON DELETE
CASCADE`). The app warns you first if they still owe money.

**Only credit carries a due date.** A payment is settled the moment it happens —
enforced by a `CHECK` constraint, not just by the UI.

---

## Security

- Passwords hashed with bcrypt. Plain text is never stored or logged.
- Every SQL query is parameterised (bound `:name` parameters, via SQLAlchemy).
  No string concatenation, and no user input ever reaches a statement as text.
- Every query filters by `user_id` from the verified token, so data cannot leak
  across accounts.
- Login returns the same message for an unknown email and a wrong password, so
  the endpoint cannot be used to discover which emails have accounts.
- Validation runs on the server regardless of what the browser checked.
- Database errors are logged on the server; the browser sees
  "Something went wrong. Please try again."
- Secrets come from `.env`, which is git-ignored.
- Signature and photo uploads must be `data:image/...` URIs and are size-capped.

---

## Money formatting

All amounts display as South African Rand: `R500.00`, `R1,250.00`, `R18,500.00`.
Formatting is done by `App.formatCurrency` in `frontend/js/app.js` — one function,
used everywhere.
