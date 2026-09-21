# Credit Book API

Every endpoint, with its authentication requirement, request body, response body
and error responses. This is the contract `frontend/js/api.js` was written
against; it did not change in the migration from Express to FastAPI.

An interactive version is served at `/api/docs` while the backend is running.

## Conventions

**Base URL** `/api` (same origin as the frontend), or
`http://localhost:5000/api` when the pages are served from somewhere else.

**Success** — HTTP 200 unless noted, always this envelope:

```json
{ "success": true, "data": … }
```

**Failure** — always this envelope, never a bare status code or an HTML page:

```json
{ "success": false, "message": "Customer not found." }
```

`message` is written for the shop owner, not for a developer. Technical detail
is logged on the server and never sent to the browser.

**Authentication** — `Authorization: Bearer <token>` on every endpoint marked
*yes*. The token is HS256, carries the user id in `sub`, and expires after
`JWT_EXPIRES_IN` (default 30 days).

**Money** is a JSON number rounded to cents (`254`, `0.9`, `2079.96`). It is
computed in `Decimal` throughout and only becomes a number at the response
boundary.

**Dates** — `dueDate` and any date-only field is `"YYYY-MM-DD"`.
`createdAt` / `updatedAt` are UTC ISO strings ending in `Z`.

**Errors common to every authenticated endpoint**

| Status | When | Message |
|---|---|---|
| 401 | no token, wrong scheme, malformed token | `Please log in to continue.` |
| 401 | expired token | `Your session has expired. Please log in again.` |
| 404 | the record belongs to another account, or does not exist | `… not found.` |
| 413 | body larger than `JSON_BODY_LIMIT` | `That upload is too large. Please use a smaller photo.` |
| 500 | bug or outage | `Something went wrong. Please try again.` |

A body that is not valid JSON returns **400** `Invalid request format.`
An unmatched path under `/api` returns **404** `That endpoint does not exist.`

---

## Health

### GET /api/health
**Auth** no · **Body** none

```json
{ "success": true, "data": { "status": "ok", "time": "2026-08-19T02:03:57.399Z" } }
```

---

## Authentication

### GET /api/auth/status
**Auth** no. Lets the login page hide registration once the owner has an account.

**200** `{ "success": true, "data": { "accountExists": true } }`

### POST /api/auth/register
**Auth** no · **201 Created**

```jsonc
{
  "fullName": "Thandi Nkosi",        // required, ≤ 120 chars
  "email": "thandi@example.com",     // required, valid address, lowercased
  "password": "MyPassword123",       // required, 8–200 chars
  "confirmPassword": "MyPassword123",// optional; must match if sent
  "businessName": "Corner Spaza",    // optional, ≤ 120 chars
  "businessPhone": "074 099 8882"    // optional, valid SA number
}
```

```json
{
  "success": true,
  "data": {
    "user": {
      "id": 1, "fullName": "Thandi Nkosi", "email": "thandi@example.com",
      "businessName": "Corner Spaza", "businessPhone": "074 099 8882",
      "profileImage": "",
      "createdAt": "2026-08-19T02:03:57.399Z", "updatedAt": "2026-08-19T02:03:57.399Z"
    },
    "token": "eyJhbGciOiJIUzI1NiIs…"
  }
}
```

`password_hash` is never present in any response.

| Status | Message |
|---|---|
| 400 | `Full name is required.` / `Email must be a valid email address.` / `Password must be at least 8 characters.` / `Passwords do not match.` / `Business phone must be a valid South African number, e.g. 074 099 8882.` |
| 409 | `An account with that email already exists.` |

### POST /api/auth/login
**Auth** no

```json
{ "email": "thandi@example.com", "password": "MyPassword123" }
```

**200** — same `{ user, token }` shape as register.

| Status | Message |
|---|---|
| 400 | `Email must be a valid email address.` / `Password is required.` |
| 401 | `Incorrect email or password.` — identical for an unknown email and a wrong password, deliberately |

### POST /api/auth/logout
**Auth** no · **Body** none. Tokens are stateless; the client discards its own.

**200** `{ "success": true, "data": { "message": "Logged out." } }`

### GET /api/auth/me
**Auth** yes · **Body** none · **200** the `user` object above.

### PATCH /api/auth/me · PUT /api/auth/me
**Auth** yes. Only the keys actually sent are updated.

```jsonc
{
  "fullName": "Thandi Nkosi",              // optional, ≤ 120 chars
  "businessName": "Corner Spaza",          // optional, ≤ 120; "" clears it
  "businessPhone": "074 099 8882",         // optional; "" clears it
  "profileImage": "data:image/png;base64,…"// optional data: URI, ≤ 4 MB
}
```

**200** the updated `user`.

| Status | Message |
|---|---|
| 400 | `Full name is required.` / `Business phone must be a valid South African number…` / `Profile photo must be an uploaded image.` |

### POST /api/auth/change-password
**Auth** yes

```jsonc
{
  "currentPassword": "MyPassword123",
  "newPassword": "MyNewPassword456",     // 8–200 chars
  "confirmPassword": "MyNewPassword456"  // optional; must match if sent
}
```

**200** `{ "success": true, "data": { "message": "Password updated." } }`

| Status | Message |
|---|---|
| 400 | `Your current password is incorrect.` / `New password must be at least 8 characters.` / `New passwords do not match.` |

---

## Customers

The customer object, returned by every customer endpoint:

```json
{
  "id": 12,
  "fullName": "Thando Mkhize",
  "phone": "074 099 8882",
  "email": null,
  "address": "Umlazi",
  "gender": "female",
  "notes": null,
  "balance": 254,
  "totalCredit": 254,
  "totalPaid": 0,
  "transactionCount": 1,
  "dueDate": "2030-01-01",
  "status": "OWING",
  "createdAt": "2026-08-19T02:03:57.399Z",
  "updatedAt": "2026-08-19T02:03:57.399Z"
}
```

`balance`, `totalCredit`, `totalPaid`, `dueDate` and `status` are **derived from
the ledger on every read** — none of them is stored.
`status` is `PAID` (nothing owed), `OVERDUE` (owed and a due date has passed) or
`OWING`.

### GET /api/customers
**Auth** yes

| Query | Meaning |
|---|---|
| `search` (or `q`) | matches name or phone; digits typed without spaces still match a phone stored with them |
| `status` | `OWING` · `PAID` · `OVERDUE` · `ALL` |

**200** `data` is an array of customers, ordered by name.

### POST /api/customers
**Auth** yes · **201 Created**

```jsonc
{
  "fullName": "Thando Mkhize",  // required, ≤ 120 chars (alias: "name")
  "phone": "074 099 8882",      // required, valid SA number, unique per account
  "email": "t@example.com",     // optional
  "address": "Umlazi",          // optional, ≤ 200 chars (alias: "area")
  "gender": "female",           // optional, "male" or "female"
  "notes": "Pays on Fridays"    // optional, ≤ 1000 chars
}
```

**201** the new customer, with `balance: 0` and `status: "PAID"`.

| Status | Message |
|---|---|
| 400 | `Full name is required.` / `Phone number must be a valid South African number, e.g. 074 099 8882.` / `Gender must be male or female.` |
| 409 | `You already have a customer with that phone number.` |

### GET /api/customers/{id}
**Auth** yes · **200** the customer · **400** `Customer ID is not valid.` · **404** `Customer not found.`

### PUT /api/customers/{id} · PATCH /api/customers/{id}
**Auth** yes. Same fields as create, all optional; only the keys sent are
written, so a partial update cannot blank out fields you did not mention.

**200** the updated customer. Errors as for create, plus 404.

### DELETE /api/customers/{id}
**Auth** yes. Their transactions and reminders go with them (`ON DELETE CASCADE`).

**200** `{ "success": true, "data": { "message": "Customer deleted." } }` · **404** `Customer not found.`

---

## Transactions

The transaction object:

```json
{
  "id": 280,
  "customerId": 12,
  "customerName": "John Example",
  "type": "CREDIT",
  "amount": 254,
  "description": "Bread ×2, Perfume, Milk ×3, Airtime",
  "dueDate": "2030-01-01",
  "notes": null,
  "signature": null,
  "productPhoto": null,
  "items": [
    { "id": 1, "name": "Bread",   "quantity": 2, "unitPrice": 15,  "lineTotal": 30 },
    { "id": 2, "name": "Perfume", "quantity": 1, "unitPrice": 120, "lineTotal": 120 },
    { "id": 3, "name": "Milk",    "quantity": 3, "unitPrice": 18,  "lineTotal": 54 },
    { "id": 4, "name": "Airtime", "quantity": 1, "unitPrice": 50,  "lineTotal": 50 }
  ],
  "itemCount": 4,
  "createdAt": "2026-08-19T02:03:57.399Z"
}
```

`runningBalance` is present **only** on `GET /api/customers/{id}/transactions`,
where it is the balance as it stood immediately after that transaction.

### GET /api/customers/{id}/transactions
**Auth** yes. The customer's ledger, newest first.

**200**

```json
{ "success": true, "data": { "customer": { … }, "transactions": [ … ] } }
```

**404** `Customer not found.`

### POST /api/customers/{id}/transactions
**Auth** yes · **201 Created**. Two request shapes are accepted.

**Multi-item credit** — the server computes every line total and the grand total:

```jsonc
{
  "type": "CREDIT",
  "dueDate": "2030-01-01",                 // optional, YYYY-MM-DD
  "description": "Month-end shop",         // optional; defaults to a summary of the items
  "items": [                               // 1–50 lines
    { "name": "Bread",   "quantity": 2, "unitPrice": 15 },
    { "name": "Perfume", "quantity": 1, "unitPrice": 120 },
    { "name": "Milk",    "quantity": 3, "unitPrice": 18 },
    { "name": "Airtime", "quantity": 1, "unitPrice": 50 }
  ],
  "notes": "…",                            // optional, ≤ 1000 chars
  "signature": "data:image/png;base64,…",  // optional data: URI, ≤ 4 MB
  "productPhoto": "data:image/jpeg;base64,…"
}
```

`quantity` must be a whole number ≥ 1; `unitPrice` must be > 0 with at most two
decimals. **An `amount` sent alongside `items` is ignored**, not trusted.

**Single amount** — payments, or a credit captured in a hurry:

```jsonc
{
  "type": "PAYMENT",              // or "CREDIT"
  "amount": 200,                  // > 0, at most two decimals
  "description": "Cash payment",  // required for CREDIT; a PAYMENT defaults to "Payment received"
  "dueDate": null                 // CREDIT only — a payment may not carry one
}
```

**201** — the transaction *and* the customer, because every caller immediately
needs the new balance:

```json
{ "success": true, "data": { "transaction": { … }, "customer": { … } } }
```

The header row and all of its item rows are written in **one database
transaction**, holding a row lock on the customer. A partial write cannot occur,
and two payments submitted at the same instant cannot both pass the overpayment
check.

| Status | Message |
|---|---|
| 400 | `Transaction type must be one of: CREDIT, PAYMENT.` |
| 400 | `Amount must be greater than zero.` / `Amount cannot have more than two decimal places.` |
| 400 | `Description is required.` |
| 400 | `Due date must be in YYYY-MM-DD format.` / `Due date is not a real date.` |
| 400 | `A payment cannot have a due date.` / `A payment cannot have item lines.` |
| 400 | `Items must be a list.` / `Add at least one item.` / `A transaction cannot have more than 50 items.` |
| 400 | `Item 2 (Perfume): quantity must be at least 1.` / `… must be a whole number.` / `… quantity is too large.` |
| 400 | `Item 2 (Perfume) unit price must be greater than zero.` |
| 400 | `Payment is more than the balance owed (R200.00). Enter that amount or less.` |
| 400 | `John Example does not owe anything, so there is nothing to pay off.` |
| 404 | `Customer not found.` |

### GET /api/transactions
**Auth** yes. The whole-business feed, newest first.

| Query | Meaning |
|---|---|
| `type` | `CREDIT` or `PAYMENT` |
| `from` | `YYYY-MM-DD`, inclusive |
| `to` | `YYYY-MM-DD`, inclusive of the whole day |
| `limit` | default 200, capped at 1000 |

**200** `data` is an array of transactions. **400** for a malformed date.

### GET /api/transactions/{id}
**Auth** yes · **200** one transaction with its items · **404** `Transaction not found.`

### DELETE /api/transactions/{id}
**Auth** yes. Item rows go with it; the balance recalculates because it is derived.

**200** `{ "success": true, "data": { "message": "Transaction deleted." } }` · **404** `Transaction not found.`

---

## Reminders

```json
{
  "id": 5, "customerId": 12,
  "customerName": "Thando Mkhize", "customerPhone": "074 099 8882",
  "amount": 350, "dueDate": "2030-01-01",
  "status": "PENDING", "urgency": "UPCOMING", "notes": "Follow up",
  "createdAt": "2026-08-19T02:03:57.399Z", "updatedAt": "2026-08-19T02:03:57.399Z"
}
```

`status` is `PENDING` · `SENT` · `DONE` · `CANCELLED`.
`urgency` is derived from the due date: `OVERDUE`, `DUE_TODAY`, `DUE_SOON`
(within 7 days), `UPCOMING`, or `CLOSED` once the status is `DONE`/`CANCELLED`.

### GET /api/reminders
**Auth** yes · queries `status` (a status, or `OPEN` for PENDING+SENT) and
`customerId`. Ordered by due date, soonest first.

### POST /api/reminders
**Auth** yes · **201 Created**

```jsonc
{
  "customerId": 12,          // required, must belong to you
  "amount": 350,             // required, > 0
  "dueDate": "2030-01-01",   // required, YYYY-MM-DD
  "status": "PENDING",       // optional
  "notes": "Follow up"       // optional, ≤ 1000 chars
}
```

| Status | Message |
|---|---|
| 400 | `Reminder amount must be greater than zero.` / `Due date must be in YYYY-MM-DD format.` / `Status must be one of: PENDING, SENT, DONE, CANCELLED.` |
| 404 | `Customer not found.` |

### GET /api/reminders/{id} · PUT/PATCH /api/reminders/{id} · DELETE /api/reminders/{id}
**Auth** yes. Update takes `amount`, `dueDate`, `status`, `notes`, all optional.
**404** `Reminder not found.` Delete returns `{ "message": "Reminder deleted." }`.

---

## Reports

Every figure is computed from the ledger in SQL. Nothing is cached, and nothing
is summed in the browser.

### GET /api/reports/summary
**Auth** yes

```json
{
  "success": true,
  "data": {
    "totalCustomers": 4,
    "totalOutstanding": 1404, "totalOverdue": 800,
    "customersOwing": 3, "customersOverdue": 1, "customersDueToday": 0,
    "totalCreditIssued": 1854, "totalPayments": 450,
    "paidThisMonth": 450, "creditThisMonth": 1854,
    "paidToday": 450, "creditToday": 1854
  }
}
```

### GET /api/reports/dashboard
**Auth** yes. Everything the dashboard renders, in one request.

```json
{
  "success": true,
  "data": {
    "summary": { … },
    "topDebtors": [
      { "id": 3, "fullName": "…", "phone": "…", "balance": 800,
        "dueDate": "2026-08-14", "status": "OVERDUE" }
    ],
    "overdueCustomers": [
      { "id": 3, "fullName": "…", "phone": "…", "balance": 800,
        "dueDate": "2026-08-14", "daysOverdue": 5, "status": "OVERDUE" }
    ],
    "recentTransactions": [ … ],
    "upcomingReminders": [ … ]
  }
}
```

### GET /api/reports?days=30
**Auth** yes. `days` is clamped to 1–365; anything unparseable falls back to 30.

```json
{
  "success": true,
  "data": {
    "summary": { … },
    "topDebtors": [ … ],
    "overdueCustomers": [ … ],
    "transactionsByDate": [
      { "date": "2026-08-19", "credit": 1854, "payments": 450, "count": 6 }
    ]
  }
}
```

---

## Items (quick entry)

```json
{ "id": 7, "name": "Bread", "price": 18.5, "createdAt": "2026-08-19T02:03:57.399Z" }
```

### GET /api/items
**Auth** yes · **200** an array, ordered by name.

### POST /api/items
**Auth** yes · **201 Created** · `{ "name": "Bread", "price": 18.5 }`

| Status | Message |
|---|---|
| 400 | `Item name is required.` / `Price must be greater than zero.` |
| 409 | `You already have a quick item with that name.` |

### DELETE /api/items/{id}
**Auth** yes · **200** `{ "message": "Item deleted." }` · **404** `Item not found.`

---

# ThathaCash endpoints

Added for the ThathaCash validation MVP (migration `0002`). Same conventions as
above: `{ "success": true, "data": … }`, Bearer token on every endpoint, money
as JSON numbers, dates as `YYYY-MM-DD`. The rules behind every derived number
are in `app/services/shop_rules.py`.

## Products / stock (extends Items)

The item object now also carries stock fields. `status` is derived, never stored:
`LOW` when `quantity <= lowStockLevel`, otherwise `GOOD`.

```json
{
  "id": 7, "name": "Coca-Cola 2L", "price": 28,
  "quantity": 5, "lowStockLevel": 6, "reorderQuantity": 12,
  "status": "LOW", "createdAt": "2026-09-17T06:49:56.649Z"
}
```

`price` is what the owner pays per unit; it prices the suggested order.

### POST /api/items
`name` and `price` required. `quantity` (default 0), `lowStockLevel` (default 5)
and `reorderQuantity` (default 10, minimum 1) are optional whole numbers, so the
original `{ "name", "price" }` body still works.

### PATCH /api/items/{id}
Any of `name`, `price`, `quantity`, `lowStockLevel`, `reorderQuantity`. Only the
keys sent change. **200** the updated item.

| Status | Message |
|---|---|
| 400 | `Quantity must be a whole number.` / `Quantity must be at least 0.` / `Order quantity must be at least 1.` / `Price must be greater than zero.` |
| 404 | `Product not found.` |

## Cash entries

`type` is one of:

| type | Owner sees | Cash |
|---|---|---|
| `OPENING` | Starting cash | in |
| `INCOME` | Money in | in |
| `EXPENSE` | Expense | out |
| `STOCK` | Stock purchase | out |
| `DRAW` | Draw | out |

```json
{ "id": 3, "type": "DRAW", "amount": 200, "note": "Personal",
  "date": "2026-09-17", "createdAt": "2026-09-17T08:10:00.000Z" }
```

### POST /api/cash · 201
```json
{ "type": "DRAW", "amount": 200, "note": "Personal", "date": "2026-09-17" }
```
`note` optional (≤ 200 chars). `date` optional, defaults to today.

| Status | Message |
|---|---|
| 400 | `Type must be one of: OPENING, INCOME, EXPENSE, STOCK, DRAW.` / `Amount must be greater than zero.` / `Amount cannot have more than two decimal places.` / `Date must be in YYYY-MM-DD format.` |

### GET /api/cash?type=&from=&to=
Newest first. `from`/`to` inclusive. `totals` always covers **every type** in the
period, even when `type` narrows the list.

```json
{
  "entries": [ … ],
  "totals": { "opening": 3000, "income": 3680, "expenses": 350,
              "stock": 1800, "draws": 330, "moneyOut": 2480 }
}
```

### GET /api/cash/summary
```json
{ "cashAvailable": 4200, "keptForExpenses": 1260, "availableForStock": 2940,
  "reservePercent": 30, "drawsThisMonth": 330, "hasEntries": true }
```
Cash available = opening + income − expenses − stock − draws (all time).
Available for stock = 70%, rounded **down** to whole rands. Both parts are 0 when
cash is 0 or negative.

### DELETE /api/cash/{id}
**200** `{ "message": "Entry deleted." }` · **404** `Entry not found.`

## GET /api/home
Everything the Home screen shows, in one request.
```json
{
  "cash": { …same as /cash/summary… },
  "order": { "total": 1187, "itemCount": 4, "withinBudget": true },
  "stock": { "items": [ …first 5, running low first… ], "lowCount": 4, "totalCount": 8 },
  "recentEntries": [ …latest 5… ]
}
```

## GET /api/order
Every running-low product × its `reorderQuantity` × its `price`, emptiest first.
```json
{
  "items": [ { "id": 9, "name": "Cooking Oil 750ml", "inStock": 2,
               "orderQuantity": 6, "unitPrice": 38.5, "lineTotal": 231 } ],
  "total": 1187, "availableForStock": 2940, "withinBudget": true
}
```
The order is only a suggestion; nothing is saved. The app shares it on WhatsApp
and the owner logs a `STOCK` entry when they pay.
