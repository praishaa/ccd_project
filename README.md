# Cloud-Based Smart Blood Donation Management System - Local Development

FastAPI + PostgreSQL backend, React (Vite) frontend. Uses **synthetic demo data only**.
Matching, priority scores and the ML forecast are decision support, not medical advice.

```
blood-donation/
├── docker-compose.yml        # local PostgreSQL
├── backend/
│   ├── app/                  # FastAPI application
│   │   ├── main.py           # app + routers + /health
│   │   ├── models.py         # tables
│   │   ├── schemas.py        # request/response models
│   │   ├── auth.py           # JWT + role-based access control
│   │   ├── services.py       # compatibility, eligibility, matching, priority
│   │   ├── ml.py             # demand forecast (scikit-learn)
│   │   ├── seed.py           # demo data
│   │   └── routers/          # auth, donors, requests, inventory, notifications, analytics
│   ├── tests/                # pytest (15 tests)
│   ├── Dockerfile
│   └── requirements.txt
└── frontend/                 # React + Vite
```

## 0. Install once

| Tool | Check with |
|---|---|
| Python 3.10+ | `python --version` (use `python3` on macOS/Linux) |
| Node.js 18+ | `node --version` |
| Docker Desktop (optional) | `docker --version` |
| Git | `git --version` |

No Docker? Skip step 1 and use the SQLite option in step 2.

## 1. Start PostgreSQL (Docker)

```bash
docker compose up -d
docker compose ps          # db should say "running"
```

## 2. Backend

macOS / Linux:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Windows (PowerShell):
```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1        # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt
copy .env.example .env
```

**No Docker?** Open `backend/.env`, put a `#` in front of the `postgresql...` line and remove the `#` from
`DATABASE_URL=sqlite:///./blood.db`.

Load demo data, then run the API:
```bash
python -m app.seed --reset
uvicorn app.main:app --reload
```

- API docs (try every endpoint): http://localhost:8000/docs
- Health check: http://localhost:8000/health

Tables are created automatically on startup.

## 3. Run the tests

In the `backend` folder with the venv active:
```bash
pytest -v
```

## 4. Frontend

Open a **second terminal**:
```bash
cd frontend
cp .env.example .env        # Windows: copy .env.example .env
npm install
npm run dev
```
Open http://localhost:5173

## 5. Demo logins

| Role | Email | Password |
|---|---|---|
| Admin | admin@bloodsys.com | Admin@123 |
| Hospital | city.hospital@bloodsys.com | Hospital@123 |
| Blood bank | redcross@bloodsys.com | Hospital@123 |
| Donor | donor1@bloodsys.com ... donor60@bloodsys.com | Donor@123 |

New donors and hospitals can register from the login page. Admins cannot self-register (seed only).

## 6. Try the whole flow (5 minutes)

1. Log in as **city.hospital@bloodsys.com** -> Requests -> create `O+`, 3 units, `critical`, city `Udupi`.
   The page reports how many matching donors were notified. Click **Donors** on the row to see them.
2. Log out, log in as a donor in Udupi (`donor1@bloodsys.com`, `donor5@...` etc.; cities rotate Udupi,
   Manipal, Mangalore, Bengaluru by donor number). Open **Alerts** to see the notification and the dashboard
   to see the open request.
3. As the donor, click **Record donation**. Eligibility changes to "In 90 days". A second donation is rejected.
4. Log in as **redcross@bloodsys.com** -> Inventory. O+ shows **Low Stock** (4 of 10). Receive 10 units
   and the status turns OK.
5. Log in as **admin@bloodsys.com** -> Analytics: charts, low-stock banner and the **AI forecast**
   (O+ demand is rising in the seed data). Inventory -> **Run low-stock check** creates alerts.

## 7. API summary (all under http://localhost:8000)

| Method + path | Who | Purpose |
|---|---|---|
| POST /auth/register, /auth/login | public | sign up / get JWT |
| GET /auth/me | any | current user |
| GET, PUT /donors/me | donor | profile, availability, eligibility |
| GET, POST /donors/me/donations | donor | donation history, record donation (90-day rule) |
| GET /donors | admin, hospital | search donors |
| POST /requests | hospital, admin | create request, run matching, notify donors |
| GET /requests, /requests/{id}, /requests/{id}/matches | hospital (own), admin | list, details, matched donors |
| GET /requests/nearby | donor | open requests the donor can serve |
| PATCH /requests/{id}/status | owner, admin | fulfilled / cancelled |
| GET /inventory, PUT /inventory/{group} | hospital, admin | stock, minimum threshold |
| POST /inventory/{group}/receive, /issue, /expire | hospital, admin | update units |
| GET /inventory/alerts, POST /inventory/check-alerts | hospital / admin | low-stock detection and notifications |
| GET /notifications, POST /notifications/{id}/read | any | alerts |
| GET /analytics/summary, /trends, /forecast | admin, hospital | dashboard data and ML forecast |

## 8. Business rules (edit in `backend/app/services.py`)

- **Compatibility**: standard red-cell ABO/Rh table (`COMPATIBLE_DONORS`).
- **Eligibility**: 90 days since last donation (`DONATION_INTERVAL_DAYS` in `.env`).
- **Matching**: compatible group + same city (case-insensitive) + available + eligible. Exact group first,
  then the longest-rested donors.
- **Priority (0-100)**: urgency (up to 60) + units (up to 20) + days remaining (up to 10) + stock shortage (10).
  High is 70 or more, Medium is 45 or more.
- **Forecast**: linear regression on the last 6 complete months of requested units per blood group; "rising"
  means 15% or more above the recent 3-month average; shortage risk means forecast demand exceeds current stock.

## 9. Commit to GitHub

```bash
git init
git add .
git commit -m "Local development version: FastAPI backend, React frontend, tests"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```
`.gitignore` already excludes `venv`, `node_modules`, `.env` and the SQLite file. Never commit `.env`.

## 10. How this maps to Azure (next phase)

| Local piece | Azure replacement |
|---|---|
| Docker Postgres / `DATABASE_URL` | Azure Database for PostgreSQL (just change `DATABASE_URL`) |
| `backend/Dockerfile` | runs on the Azure Virtual Machine |
| `notifications` table | keep it, and also push events to Azure Notification Hubs |
| `POST /inventory/check-alerts` | called on a schedule by an Azure Function (timer trigger) |
| `/health` and console logs | Azure Monitor / Application Insights |
| frontend `npm run build` output (`dist/`) | Azure Blob Storage static site, or served from the VM |

## Troubleshooting

| Problem | Fix |
|---|---|
| `connection refused` on port 5432 | `docker compose up -d`, wait 10 seconds, or switch to SQLite in `.env` |
| `port 5432 is already allocated` | another Postgres is running; stop it, or use SQLite |
| Frontend shows "Cannot reach the server" | backend not running, or `VITE_API_URL` in `frontend/.env` is wrong |
| Browser CORS error | frontend must run on port 5173, or add its URL to `CORS_ORIGINS` in `backend/.env` |
| Login says incorrect email or password | run `python -m app.seed --reset` and use the demo logins above |
| `ModuleNotFoundError: app` | run commands from inside the `backend` folder |
| Activate.ps1 blocked on Windows | `Set-ExecutionPolicy -Scope Process Bypass` |
| Forecast table shows "insufficient data" | seed data has 8 months of history; run `python -m app.seed --reset` |
