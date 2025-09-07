# ERISA Dev Challenge – Claims Management (Django + HTMX)

A small Django app that ingests claim data, lists claims with search and status filtering, shows **HTMX**-powered claim detail without full page reloads, and supports **flagging** and **notes**. A simple **dashboard** summarizes totals, underpayment, and top payers.

---

## Features

- **Data ingestion** from CSV via a Django management command
- **Claims list** with:
  - Search (by claim ID / patient name / payer)
  - Status filter (All, Denied, Pending, Appealed, Paid, Under Review)
  - “View” opens a claim’s **detail inline** (HTMX)
- **Claim detail**:
  - Patient, payer, billed/paid, service date
  - CPT codes & denial reason
  - **Flag / Unflag** (HTMX)
  - **Notes** (requires login; add/update list inline via HTMX)
  - “Back to list” swaps the table back into view
- **Dashboard** with basic aggregates and recent notes
- Clean, minimal styling via `static/css/app.css`

---

## Requirements

- Python **3.11+** (3.12 recommended)
- pip
- SQLite (bundled with Python)

---

## Quick Start (Windows PowerShell)

```powershell
# 1) Create & activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Run migrations
python manage.py migrate

# 4) Create a superuser
python manage.py createsuperuser

# 5) Import sample data (CSV files shipped in the repo root)
python manage.py import_erisa_data --list .\claim_list_data.csv --detail .\claim_detail_data.csv --mode overwrite

# 6) Start the dev server
python manage.py runserver
