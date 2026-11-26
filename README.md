# SpendWise

A personal finance tracker: backend API plus a small web page. Built with **FastAPI**, **SQLAlchemy 2.0**
and **PostgreSQL** (SQLite works too, for zero-setup local runs). Includes JWT auth, categories,
income/expense tracking, monthly reports, CSV export and automated tests.

## Features
- Register / login (JWT, bcrypt-hashed passwords); every user sees only their own data
- Income and expense transactions with category, note and date
- Filter by type, category, date range and note search; pagination
- Monthly report: income, expenses, balance and expenses by category (SQL aggregation)
- CSV export
- Web page at `/` to use everything without Swagger, with readable error messages
- Money stored as integer cents (no floating-point rounding errors)
- 25 automated tests and a `check.py` self-diagnosis script

## Quick start (Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python check.py                              # checks your setup and the whole app
python -m pytest -v                          # run the tests
python -m uvicorn app.main:app --reload      # start the app
```
Open **http://127.0.0.1:8000** (web page) or **http://127.0.0.1:8000/docs** (API docs).
If activation is blocked, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first.

## Using PostgreSQL
1. Create an empty database named `spendwise`.
2. Copy `.env.example` to `.env`, uncomment the PostgreSQL `DATABASE_URL` line and set your password.
3. Run `python check.py` to confirm the connection, then start the app. Tables are created automatically.

## API
| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Get JWT (form data) |
| GET | `/api/auth/me` | Current user |
| POST / GET | `/api/categories` | Create / list categories |
| DELETE | `/api/categories/{id}` | Delete category (transactions are kept) |
| POST / GET | `/api/transactions` | Create / list (`type`, `category_id`, `date_from`, `date_to`, `search`, `skip`, `limit`) |
| GET | `/api/transactions/export` | CSV download (same filters) |
| GET / PATCH / DELETE | `/api/transactions/{id}` | Read / update / delete |
| GET | `/api/reports/monthly?year=&month=` | Income, expenses, balance, expenses by category |

## Project layout
```
app/
  main.py            app setup, serves the web page
  config.py          settings from environment / .env
  database.py        engine and session
  models.py          User, Category, Transaction
  schemas.py         request/response validation
  security.py        password hashing, JWT
  deps.py            current-user dependency
  routers/           auth, categories, transactions, reports
  static/index.html  web page (plain HTML + JavaScript)
tests/               pytest suite (in-memory SQLite)
check.py             self-diagnosis script
```

## Design notes
- **Integer cents** for money: exact arithmetic, and sums happen in the database.
- Every query filters by `user_id`, so users can never read each other's data.
- Composite index on `(user_id, occurred_on)` for the date-range queries used by reports and lists.
- Deleting a category sets its transactions' category to `NULL` instead of deleting them.
- `PATCH` uses `exclude_unset`: omitted fields stay unchanged, `category_id: null` clears the category.

## Ideas to extend
- Alembic migrations, budgets with alerts, recurring transactions, Docker, deployment
