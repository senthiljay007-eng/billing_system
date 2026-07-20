# Billing System

A Django app for generating customer bills, emailing invoices asynchronously,
computing change-denomination breakdowns, and browsing a customer's previous
purchases.

## Setup

This project uses **PostgreSQL**. If you don't have it installed, download it
from https://www.postgresql.org/download/ (the Windows installer also
includes `psql` and pgAdmin, and lets you set the `postgres` superuser
password during install — remember what you choose).

### 1. Create the database

Open a terminal and run `psql` as the `postgres` superuser (you'll be
prompted for the password you set during install):

```bash
psql -U postgres
```

Then, at the `psql` prompt:

```sql
CREATE DATABASE billing_system;
\q
```

(You can also do this visually in pgAdmin: right-click **Databases** →
**Create** → **Database**, name it `billing_system`.)

### 2. Configure credentials

Copy `.env.example` to `.env` (same folder as `manage.py`) and fill in the
password you used above:

```bash
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux
```

`.env` looks like this — only `DB_PASSWORD` normally needs changing if
you used a non-default username/host/port:

```
DB_NAME=billing_system
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
```

`.env` is git-ignored, so your real password never gets committed. Django
reads it automatically on startup (see `load_dotenv(...)` in
`billing_project/settings.py`).

### 3. Install dependencies and initialize the app

```bash
# from the billing_system/ directory (where manage.py lives)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

python manage.py migrate
python manage.py seed_data        # creates sample products + default shop denominations
python manage.py createsuperuser  # optional, for /admin/
python manage.py runserver
```

If `migrate` fails with a connection/authentication error, double-check
that PostgreSQL is running (`Get-Service *postgres*` on Windows) and that
the values in your `.env` file match what you set up in step 1.

Visit:
- `http://127.0.0.1:8000/` — Page 1, generate a bill.
- `http://127.0.0.1:8000/purchases/` — look up a customer's previous purchases by email.
- `http://127.0.0.1:8000/admin/` — manage Products and Denominations (CRUD via Django admin).

## Testing the flow

1. Run `seed_data` to get products `P001`-`P005` and default denomination
   counts (500, 50, 20, 10, 5, 2, 1).
2. On Page 1, enter a customer email, click **Add New** to add product rows
   (use a seeded Product ID and a quantity), adjust denomination counts if you
   like, enter a cash amount, and click **Generate Bill**.
3. You'll be redirected to Page 2 with the computed totals and change
   breakdown. The invoice email is sent on a background thread; since the
   default email backend is the console backend, the full email text is
   printed to the terminal running `runserver` (no real inbox needed to
   verify the "send asynchronously" requirement).
4. Go to **View Previous Purchases**, enter the same customer email, and
   confirm the invoice you just created is listed; click **View items** to
   see the line items again.

## Running the tests

`billing/tests.py` covers the change-making logic, the full bill-generation
flow (totals, stock deduction, insufficient-payment rejection), and a smoke
test for each of the three pages. Django automatically creates and drops a
temporary test database, using the same `.env` credentials, so no extra
setup is needed beyond step 1-2 above:

```bash
python manage.py test
```

## Assumptions

- **Product ID** is a separate human-readable SKU field (`P001`, `P002`, ...)
  distinct from Django's internal numeric primary key, since the spec lists
  "product ID" as its own field alongside "name".
- **Price / tax fields use `float`** per the spec's explicit "(float)"
  annotations, rounded to 2 decimals wherever displayed/stored on the
  invoice. (Decimal would be the stricter choice for real money, but the
  spec asked for float.)
- **Denomination stock is persisted** (`Denomination` model, seeded with
  defaults, editable via admin). The Page 1 form pre-fills the current shop
  counts, but the cashier can adjust them each time (e.g. after recounting
  the till) — those adjusted counts are what's used to compute change. After
  a bill is generated, whichever notes were handed back as change are
  deducted from that stored count, so the till reflects reality on the next
  visit.
- **Change is computed greedily** from the largest denomination down,
  bounded by whatever counts were submitted for that bill. If the available
  notes genuinely can't cover the exact balance, the shortfall is shown as an
  "unresolved" amount on Page 2 rather than silently failing.
- **Rounding**: the net price (before change is calculated) is rounded
  *down* to the nearest whole currency unit, matching the worked example in
  the spec (2357.60 -> 2357.00), and the balance due to the customer is
  calculated against that rounded-down figure.
- **Async email**: sent via a background `threading.Thread` rather than a
  task queue like Celery, so the project has no extra infrastructure
  (broker, worker process) to set up and is guaranteed to run on any
  machine with just `pip install -r requirements.txt`. The default
  `EMAIL_BACKEND` is Django's console backend, so invoices print to the
  terminal instead of requiring real SMTP credentials to evaluate. To send
  real email, set environment variables before running the server:
  ```bash
  export EMAIL_BACKEND=smtp
  export EMAIL_HOST=smtp.gmail.com
  export EMAIL_HOST_USER=you@gmail.com
  export EMAIL_HOST_PASSWORD=your-app-password
  export DEFAULT_FROM_EMAIL=you@gmail.com
  ```
- **PostgreSQL driver**: the app connects via `psycopg` (v3), Django's
  officially supported driver alongside `psycopg2`. It's used here instead
  of `psycopg2-binary` purely because `psycopg2-binary` doesn't yet ship a
  prebuilt wheel for very new Python versions (e.g. 3.14) and would require
  a local C++ compiler to build from source; `psycopg` installs cleanly
  everywhere and Django's `ENGINE = 'django.db.backends.postgresql'` works
  with either driver unchanged.
- **No login/auth** is implemented — the spec didn't ask for user accounts,
  only Django admin for product/denomination CRUD (which is already
  authenticated).
- **Stock/formset validation**: submitting a Product ID that doesn't exist,
  or a quantity exceeding available stock, or cash paid less than the bill
  total, all surface as form/validation errors on Page 1 rather than
  partially creating a bill.

## Project structure

```
billing_system/
  manage.py
  requirements.txt
  README.md
  billing_project/       # Django project settings/urls
  billing/                # the app: models, views, forms, services, templates
```
