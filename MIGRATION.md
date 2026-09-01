# Credit Book — Backend Migration: Node/Express → Python/FastAPI

Status of the source system at the time of inspection:

- `npm test` → **88 tests, 88 pass, 0 fail** (18 suites, ~5.2s)
- PostgreSQL `credit_book` on `localhost:5432`, reachable
- Frontend: static HTML/CSS/vanilla JS, served by the same process as the API

The goal is a like-for-like backend replacement. Same database, same URLs, same
JSON shapes, same business rules, same frontend.

---

## 1. Existing backend structure

```
backend/
├── server.js                     boot: ping DB, listen, graceful shutdown
├── package.json
└── src/
    ├── app.js                    express app, CORS, JSON limit, static frontend
    ├── config.js                 env loading + required-var check
    ├── db/
    │   ├── pool.js               pg Pool, query/queryOne/withTransaction
    │   ├── schema.sql            the authoritative schema
    │   ├── migrate.js            applies schema.sql (--fresh drops)
    │   ├── create-database.js
    │   └── seed.js               demo data
    ├── middleware/
    │   ├── auth.js               signToken + requireAuth (JWT)
    │   └── error.js              notFoundHandler + errorHandler
    ├── routes/                   thin express routers
    ├── controllers/              request parsing + validation
    ├── services/                 business rules + SQL
    └── utils/
        ├── ApiError.js           status-carrying, user-safe error
        ├── asyncHandler.js
        ├── money.js              toAmount / parseAmount
        └── validate.js           hand-rolled field validators

backend/tests/
├── api.test.js                   auth, customers, ledger, reminders, reports, items
└── multi-item.test.js            multi-item credit transactions
```

Layering: `route → controller (validate) → service (rules + SQL) → pg`.
Errors travel as `ApiError`; anything else is logged and becomes a generic 500.

Two files are unrelated experiments and are **not** part of the running app:
`src/db/supabaseClient.js` and `src/db/test-supabase.js`. They are not required
by `app.js` and are not migrated.

---

## 2. Existing database schema

Six tables. Money is `NUMERIC(12,2)` everywhere; **no balance is ever stored** —
it is derived from the ledger on every read.

| Table | Key columns | Rules enforced by the DB |
|---|---|---|
| `users` | `id`, `full_name`, `email` UNIQUE, `password_hash`, `business_name`, `business_phone`, `profile_image`, timestamps | name non-blank, `email` contains `@` |
| `customers` | `id`, `user_id` FK→users CASCADE, `full_name`, `phone`, `email`, `address`, `gender`, `notes`, timestamps | name/phone non-blank, `gender IN (male,female)`, **UNIQUE (user_id, phone)** |
| `transactions` | `id`, `user_id` FK, `customer_id` FK CASCADE, `type`, `amount`, `description`, `due_date`, `notes`, `signature`, `product_photo`, `created_at` | `type IN (CREDIT,PAYMENT)`, `amount > 0`, description non-blank, **due_date only on CREDIT** |
| `transaction_items` | `id`, `transaction_id` FK CASCADE, `name`, `quantity` INT, `unit_price`, `line_total`, `position`, `created_at` | name non-blank, `quantity > 0`, `unit_price > 0`, `line_total > 0`, **`line_total = quantity * unit_price`** |
| `reminders` | `id`, `user_id` FK, `customer_id` FK CASCADE, `amount`, `due_date`, `status`, `notes`, timestamps | `amount >= 0`, `status IN (PENDING,SENT,DONE,CANCELLED)` |
| `items` | `id`, `user_id` FK, `name`, `price`, `created_at` | name non-blank, `price > 0`, **UNIQUE (user_id, name)** |

Indexes: `customers(user_id)`, `transactions(customer_id)`,
`transactions(user_id, created_at DESC)`, `transaction_items(transaction_id, position)`,
`reminders(user_id, due_date)`.

**This schema does not change.** SQLAlchemy models are written to match it
column-for-column and constraint-for-constraint, and the initial Alembic
revision reproduces it exactly.

---

## 3. Existing API routes → FastAPI routes

Envelope, unchanged: success `{"success": true, "data": …}`,
failure `{"success": false, "message": "…"}`.

| Method | URL | Auth | Express handler | New FastAPI location |
|---|---|---|---|---|
| GET | `/api/health` | no | `routes/index.js` inline | `api/routes/health.py` |
| GET | `/api/auth/status` | no | `auth.controller.status` | `api/routes/auth.py` |
| POST | `/api/auth/register` | no | `auth.controller.register` | `api/routes/auth.py` |
| POST | `/api/auth/login` | no | `auth.controller.login` | `api/routes/auth.py` |
| POST | `/api/auth/logout` | no | `auth.controller.logout` | `api/routes/auth.py` |
| GET | `/api/auth/me` | yes | `auth.controller.me` | `api/routes/auth.py` |
| PATCH/PUT | `/api/auth/me` | yes | `auth.controller.updateMe` | `api/routes/auth.py` |
| POST | `/api/auth/change-password` | yes | `auth.controller.changePassword` | `api/routes/auth.py` |
| GET | `/api/customers?search=&status=` | yes | `customer.controller.list` | `api/routes/customers.py` |
| POST | `/api/customers` | yes | `customer.controller.create` | `api/routes/customers.py` |
| GET | `/api/customers/{id}` | yes | `customer.controller.getOne` | `api/routes/customers.py` |
| PUT/PATCH | `/api/customers/{id}` | yes | `customer.controller.update` | `api/routes/customers.py` |
| DELETE | `/api/customers/{id}` | yes | `customer.controller.remove` | `api/routes/customers.py` |
| GET | `/api/customers/{id}/transactions` | yes | `transaction.controller.listForCustomer` | `api/routes/customers.py` |
| POST | `/api/customers/{id}/transactions` | yes | `transaction.controller.create` | `api/routes/customers.py` |
| GET | `/api/transactions?type=&from=&to=&limit=` | yes | `transaction.controller.listAll` | `api/routes/transactions.py` |
| GET | `/api/transactions/{id}` | yes | `transaction.controller.getOne` | `api/routes/transactions.py` |
| DELETE | `/api/transactions/{id}` | yes | `transaction.controller.remove` | `api/routes/transactions.py` |
| GET | `/api/reminders?status=&customerId=` | yes | `reminder.controller.list` | `api/routes/reminders.py` |
| POST | `/api/reminders` | yes | `reminder.controller.create` | `api/routes/reminders.py` |
| GET | `/api/reminders/{id}` | yes | `reminder.controller.getOne` | `api/routes/reminders.py` |
| PUT/PATCH | `/api/reminders/{id}` | yes | `reminder.controller.update` | `api/routes/reminders.py` |
| DELETE | `/api/reminders/{id}` | yes | `reminder.controller.remove` | `api/routes/reminders.py` |
| GET | `/api/reports?days=30` | yes | `report.controller.full` | `api/routes/reports.py` |
| GET | `/api/reports/summary` | yes | `report.controller.summary` | `api/routes/reports.py` |
| GET | `/api/reports/dashboard` | yes | `report.controller.dashboard` | `api/routes/reports.py` |
| GET | `/api/items` | yes | `item.controller.list` | `api/routes/items.py` |
| POST | `/api/items` | yes | `item.controller.create` | `api/routes/items.py` |
| DELETE | `/api/items/{id}` | yes | `item.controller.remove` | `api/routes/items.py` |
| * | `/api/*` unmatched | – | `notFoundHandler` | 404 handler in `main.py` |
| GET | any non-API path | – | static frontend / `index.html` | `StaticFiles` + catch-all in `main.py` |

Full per-endpoint request/response/error contracts: see
[`backend/API.md`](backend/API.md).

---

## 4. Existing authentication flow

```
POST /auth/register  →  validate → email unique? → bcrypt hash (cost 10)
                     →  INSERT users → 201 { user, token }
POST /auth/login     →  SELECT by email → bcrypt compare (dummy compare when
                        the email is unknown, so timing and message match)
                     →  200 { user, token }
Protected request    →  Authorization: Bearer <jwt>
                     →  jwt.verify(HS256, JWT_SECRET) → req.userId = Number(sub)
                     →  every query filters on user_id
```

- Token: HS256, payload `{ sub: "<userId>" }`, `expiresIn` from `JWT_EXPIRES_IN` (default `30d`).
- Missing/blank/malformed token → **401** `"Please log in to continue."`
- Expired token → **401** `"Your session has expired. Please log in again."`
- Wrong password *and* unknown email → **401** `"Incorrect email or password."` (identical, deliberately).
- `password_hash` is never selected into any API response.
- Logout is stateless: the endpoint exists so the frontend has one thing to call.

| Node | Python |
|---|---|
| `jsonwebtoken.sign/verify` | `PyJWT` (`jwt.encode/decode`, HS256) |
| `bcryptjs.hash(pw, 10)` | `bcrypt.hashpw(pw, bcrypt.gensalt(10))` |
| `bcryptjs.compare` | `bcrypt.checkpw` — existing `$2a$10$…` hashes verify unchanged |
| `requireAuth` middleware | `Depends(get_current_user_id)` in `dependencies/auth.py` |

Existing accounts keep working: the hash format and the JWT signing algorithm,
secret and claim are all unchanged, so **tokens issued by the Node backend stay
valid against the FastAPI backend.**

---

## 5. Existing frontend API dependencies

Every call goes through `frontend/js/api.js` — one module, no page builds its own
`fetch`. It expects:

- base URL `/api` (or `http://localhost:5000/api` when the pages are served elsewhere)
- `Authorization: Bearer <token>`, token in `localStorage`
- success bodies unwrapped as `payload.data`
- failure bodies read as `payload.message`; **401 clears the session and redirects to login**
- a JSON body on *every* error — a bodyless 404/405 is reported as "not the Credit Book API"

Response fields the pages actually read (all preserved):

`fullName, businessName, businessPhone, profileImage, balance, totalCredit,
totalPaid, transactionCount, dueDate, status, createdAt, customerName,
customerPhone, type, amount, description, notes, signature, productPhoto,
items[].{name,quantity,unitPrice,lineTotal}, itemCount, runningBalance,
urgency, daysOverdue, accountExists`, and the report blocks
`summary{totalOutstanding,totalOverdue,customersOwing,customersOverdue,
customersDueToday,totalCreditIssued,totalPayments,paidThisMonth,creditThisMonth,
paidToday,creditToday,totalCustomers}, topDebtors, overdueCustomers,
recentTransactions, upcomingReminders, transactionsByDate`.

Two formatting details the frontend depends on and the Python backend therefore
reproduces exactly:

1. Money is a **JSON number rounded to cents** (`30`, `0.3`, `2079.96`) — never a
   string, never `30.000000000001`.
2. `dueDate` is a plain `"YYYY-MM-DD"` string; `createdAt` is a **UTC ISO string
   ending in `Z`** with milliseconds, because `formatDateShort()` slices the
   first 10 characters of it.

**No frontend file needs to change.**

---

## 6. The existing 88 tests

`tests/api.test.js` (63) and `tests/multi-item.test.js` (25), both booting the
real app on a random port and talking HTTP. Grouped as:

| Area | Covers |
|---|---|
| health | unauthenticated 200 |
| auth | short password, bad email, register, duplicate email, wrong password, unknown email, login, no token, bad token |
| customers | blank name, bad phone, create, duplicate phone, search by name, search by digits-only phone, empty search, partial update, 404, non-numeric id |
| transactions & balance | zero/negative amount, unknown type, impossible date, unknown customer, 1000 credit − 500 paid = 500, overpayment refused, exact settlement, payment with nothing owed, due date on payment, cents without drift, >2 decimals, running balance, delete recalculates, overdue status + filter |
| reminders | unknown customer, create, overdue urgency, status update, bad status, OPEN filter, delete |
| reports | numeric totals, all dashboard sections, daily activity, outstanding reconciles with customer balances |
| items | create, duplicate name, zero price, delete |
| isolation | one account cannot list, read or delete another's customers |
| error handling | JSON 404, malformed JSON, no SQL/stack leakage |
| cascade | deleting a customer deletes their transactions |
| multi-item | single line, legacy amount form, four lines = R254, balance moves once, auto description `Bread ×2, Perfume, Milk ×3, Airtime`, description override, line maths, cent maths, client total ignored, DB check constraint, exact row count, cascade of item rows, 11 validation cases, part payment, overpayment message text, settlement, payment has no items, history with items, feed with items, fetch-by-id with items, reports reconcile |

The pytest suite recreates every one of these as
`backend/tests/test_*.py`, keeping the same assertions — including the exact
error message strings.

---

## 7. Proposed FastAPI architecture

```
backend/
├── app/
│   ├── main.py                 app factory, middleware, exception handlers,
│   │                           static frontend mount, catch-all
│   ├── api/
│   │   ├── router.py           /api aggregation
│   │   └── routes/
│   │       ├── health.py  auth.py  customers.py
│   │       ├── transactions.py  reminders.py  reports.py  items.py
│   ├── core/
│   │   ├── config.py           pydantic-settings, reads backend/.env
│   │   ├── security.py         bcrypt + JWT sign/verify
│   │   ├── errors.py           ApiError + handlers (incl. PG code → 409 map)
│   │   ├── money.py            to_amount / parse_amount (Decimal)
│   │   └── validate.py         port of utils/validate.js
│   ├── db/
│   │   ├── base.py             DeclarativeBase
│   │   └── session.py          engine, SessionLocal, get_db
│   ├── models/                 SQLAlchemy ORM, one file per table
│   ├── schemas/                Pydantic request/response models
│   ├── repositories/           all SQL lives here
│   ├── services/               business rules (ports of src/services/*)
│   └── dependencies/auth.py    get_current_user_id
├── alembic/versions/0001_initial_schema.py
├── alembic.ini
├── tests/                      pytest + TestClient
├── requirements.txt
└── API.md
```

Mapping, file by file:

| Express | FastAPI |
|---|---|
| `src/app.js` | `app/main.py` |
| `src/config.js` | `app/core/config.py` |
| `src/db/pool.js` | `app/db/session.py` |
| `src/db/schema.sql` + `migrate.js` | `app/models/*` + `alembic/versions/0001_initial_schema.py` |
| `src/middleware/auth.js` | `app/core/security.py` + `app/dependencies/auth.py` |
| `src/middleware/error.js` | `app/core/errors.py` |
| `src/utils/ApiError.js` | `app/core/errors.py :: ApiError` |
| `src/utils/money.js` | `app/core/money.py` |
| `src/utils/validate.js` | `app/core/validate.py` |
| `src/controllers/*.js` | `app/api/routes/*.py` |
| `src/services/*.js` | `app/services/*.py` (rules) + `app/repositories/*.py` (SQL) |
| `db.withTransaction(fn)` | `Session` unit of work, `with session.begin()` |
| `SELECT … FOR UPDATE` | `.with_for_update()` / `text(… FOR UPDATE)` |

Decisions taken, and why:

- **Sync SQLAlchemy 2.0 + psycopg2.** The endpoints are short DB round-trips;
  async would add failure modes without buying throughput here, and sync keeps
  the port a line-for-line comparison against the Node service.
- **ORM for writes and single-row reads, `text()` for the aggregates.** The
  balance/report SQL (window functions, `FILTER`, CTEs) is the part most likely
  to drift under translation, so it is carried across verbatim.
- **Decimal end to end, `float` only at the JSON edge**, mirroring the existing
  `toAmount` boundary — so the wire format the frontend sees is unchanged.
- **Validation stays hand-rolled** in `core/validate.py`. Pydantic defines the
  schemas, but the 400-level *messages* are user-facing copy the tests assert on
  ("must be a valid South African number…"), and FastAPI's default 422 body has
  a different shape than this frontend understands. All request validation
  errors are therefore normalised to `400 {"success": false, "message": …}`.

---

## 8. Migration risks

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| 1 | FastAPI's default `422` validation body breaks the frontend's error display | High | Global `RequestValidationError` handler → `400 {"success":false,"message":…}`; hand-rolled validators produce the same strings as today |
| 2 | Money serialised as a string (`"30.00"`) or drifting float | High | `to_amount()` at the response boundary only; Decimal for all arithmetic; assertions on `0.3`, `319.96`, `2079.96` kept from the Node suite |
| 3 | `created_at` serialised with a `+02:00` offset — `formatDateShort()` slices 10 chars and would show the wrong day near midnight | Medium | Serialise timestamps as UTC ISO with `Z` and milliseconds, exactly as `JSON.stringify(Date)` does |
| 4 | Reports/balances re-expressed in ORM query syntax quietly change a number | High | Aggregate SQL carried over verbatim inside `text()`; reconciliation tests compare report totals against summed customer balances |
| 5 | Payment race lets two concurrent payments both pass the overpayment check | High | Keep `SELECT … FOR UPDATE` on the customer row inside the same transaction, as today |
| 6 | Partial write leaves a transaction with some item rows | High | One `Session` transaction wrapping the header insert, all item inserts and the read-back; rollback on any failure; test asserts nothing is written when validation fails |
| 7 | bcrypt hashes from `bcryptjs` fail to verify | High (locks the owner out) | `$2a$` is standard bcrypt; `bcrypt.checkpw` reads it. Verified against a hash produced by the Node backend before cutover |
| 8 | Existing JWTs invalidated by the swap | Medium | Same secret, same HS256, same `sub` claim — old tokens keep working |
| 9 | Postgres integrity errors surfacing as 500 instead of the current 409 | Medium | `IntegrityError` handler maps `pgcode`/constraint name using the same table as `middleware/error.js` |
| 10 | Trailing-slash / method differences (`PUT` *and* `PATCH`; `/customers` vs `/customers/`) | Medium | Both verbs registered on the same handler; routes declared without trailing slashes to match the frontend |
| 11 | Alembic's initial revision run against the **existing populated** database would try to recreate tables | High | The revision is written to match the live schema; for the existing DB the documented step is `alembic stamp head`, not `upgrade` |
| 12 | Both backends running on port 5000 at once | Low | Only one is started at a time; the Python app reads the same `PORT` |
| 13 | Losing a behaviour that no test covers | Medium | The Node backend stays in the tree until the pytest suite passes and the frontend has been driven against FastAPI |

---

## 9. Sequence, and what actually happened

1. **Inspect** — this document. Node suite green at 88/88 as the baseline.
2. **Build the FastAPI backend alongside the Express one.** Nothing was
   deleted; both backends still run from `backend/`.
3. **Port the tests.** `pytest` — **141 passed**, against the same PostgreSQL
   database, recreating every behaviour the 88 Node tests covered plus the
   integrity, rollback and reconciliation cases the brief called for.
4. **Run both against the same database and compare.** A script drove an
   identical 91-request session against Express (port 5000) and FastAPI
   (port 5001) — every endpoint, every validation path, every error — and
   diffed status codes and response bodies. Result: **no differences**.
5. **Drive the frontend against FastAPI.** All 13 pages and 24 css/js assets
   serve correctly, and every call `frontend/js/api.js` can make returns the
   shape the pages unwrap. **No frontend file was changed.**
6. **Remove the Express backend.** Done, once everything above was green:
   `server.js`, `src/`, `package.json`, `package-lock.json`, `node_modules/`
   and the two `tests/*.test.js` files are gone. `pytest` (141), the server and
   the frontend check were all re-run afterwards against the standalone
   FastAPI backend and still pass.

### Verification results

| Check | Result |
|---|---|
| Node suite (baseline, still passing) | 88/88 |
| pytest suite | 141/141 |
| Express vs FastAPI, 91 paired requests | identical status + body on all 91 |
| Alembic revision vs the live schema | identical: 52 columns, 74 constraints, 14 indexes |
| Fresh install path (`create_database` → `alembic upgrade` → `seed`) | works; balances and line totals reconcile |
| Frontend pages / assets served | 13 / 24, all 200 |
| bcryptjs hash → Python `bcrypt.checkpw` | verifies |
| Python bcrypt hash → Node `bcryptjs.compare` | verifies |
| Node-issued JWT → FastAPI | accepted |
| FastAPI-issued JWT → Node | accepted |
| `createdAt` wire format | identical (`…Z`, milliseconds) |

The last four mean the swap is **not a flag day**: existing accounts keep their
passwords and anyone already logged in keeps their session.

### Differences found and fixed during the port

| # | Difference | Fix |
|---|---|---|
| 1 | A POST to an unknown `/api/…` path returned Starlette's **405**, where Express returned a JSON **404**. `frontend/js/api.js` reads a bodyless 405 as "this web server cannot run the Credit Book API", so a simple typo would have produced an alarming message. | The frontend catch-all now answers every method, not only GET, and returns the same JSON 404. |
| 2 | Alembic echoes a revision's first docstring line to the console; an em dash in it crashed on a Windows cp1252 terminal. | The revision message is ASCII-only. |

### Left in place, deliberately

`supabaseClient.js` and `test-supabase.js` are standalone experiments — nothing
in the app imports them — so they were not migrated and not rewritten. They
moved from `backend/src/db/` to **`backend/scripts/`** to survive the removal
of `src/`, with their `.env` lookup path adjusted for the new depth. Their keys
remain documented in `.env.example`.

They still need Node and the `@supabase/supabase-js` package, which
`package.json` no longer installs. To run one:
`npm install @supabase/supabase-js dotenv && node scripts/test-supabase.js`.
