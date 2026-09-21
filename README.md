<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python" />
  <img src="https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi" />
  <img src="https://img.shields.io/badge/TensorFlow-2.x-FF6F00?style=flat-square&logo=tensorflow" />
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react" />
  <img src="https://img.shields.io/badge/MongoDB-Atlas-47A248?style=flat-square&logo=mongodb" />
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker" />
</p>

<h1 align="center">🔬 RetinalGuard — AI Diabetic Retinopathy Detection</h1>

<p align="center">
  A full-stack clinical AI platform that detects <strong>Diabetic Retinopathy (DR)</strong> from retinal fundus images
  using <strong>EfficientNet-B0</strong> with <strong>Grad-CAM</strong> explainability, a patient portal,
  a doctor review workflow, an admin panel, and a standalone MLOps monitoring dashboard.
</p>

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🧠 **AI Model** | EfficientNet-B0 fine-tuned on the APTOS 2019 Blindness Detection dataset |
| 🔥 **Grad-CAM** | Visual heatmap overlays highlighting pathological retinal regions |
| 👤 **Patient Portal** | Upload retinal scans, view AI reports, chat with RAG-powered assistant |
| 👨‍⚕️ **Doctor Dashboard** | Real patient list, urgent-case alerts (risk ≥ 85%), one-click email referral |
| 🛡️ **Admin Panel** | User & doctor management, scan database, system analytics |
| 📊 **MLOps Dashboard** | Standalone monitoring page at `/devops` — model metrics, system health, prediction logs |
| 🔐 **Auth** | JWT + email verification, Google OAuth modal, demo bypass code |
| 🐳 **Docker** | Frontend (nginx) + Backend (uvicorn) via Docker Compose on a single VPS |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                     VPS (Docker)                    │
│                                                     │
│  ┌──────────────────┐    ┌──────────────────────┐   │
│  │  retinaguard-    │    │  retinaguard-        │   │
│  │  frontend        │───▶│  backend             │   │
│  │  (nginx : 80)    │    │  (FastAPI : 8000)    │   │
│  └──────────────────┘    └─────────┬────────────┘   │
│                                    │                │
│                          ┌─────────▼────────────┐   │
│                          │  MongoDB Atlas        │   │
│                          │  (retinaguard_db)     │   │
│                          └──────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

- **Frontend:** React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui + Recharts
- **Backend:** FastAPI (async) + Motor (async MongoDB driver)
- **AI Pipeline:** TensorFlow / Keras EfficientNet-B0 → Grad-CAM → base64 heatmap
- **RAG Chatbot:** LangChain + FAISS vector store for clinical Q&A
- **Database:** MongoDB Atlas (cloud) — collections: `users`, `scans`

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- MongoDB Atlas account

### 1. Clone the repository
```bash
git clone https://github.com/lilosman/retinaguard-fastapi.git
cd retinaguard-fastapi
```

### 2. Configure environment
Create `python-api/.env`:
```env
MONGO_URI=mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/retinaguard_fastapi_db
JWT_SECRET=your_super_secret_key
MODEL_PATH=/app/output/efficientnetb0_blindness_model.keras
```

### 3. Run locally with Docker Compose
```bash
docker-compose up --build
```
- Frontend: http://localhost:80
- Backend API: http://localhost:8000
- MLOps Dashboard: http://localhost:80/devops

### 4. Run backend only (development)
```bash
cd python-api
python -m venv venv && venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 📡 API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | Register a new patient account |
| `POST` | `/api/auth/login` | Login, returns JWT token |
| `POST` | `/api/auth/verify-email` | Verify email with 6-digit code |
| `POST` | `/api/auth/resend-code` | Resend verification code |
| `POST` | `/api/auth/google` | Instant sign-in via Google OAuth modal |

### AI / Scans
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/predict` | Upload retinal image → AI prediction + Grad-CAM |
| `GET`  | `/api/scans/my` | Get authenticated patient's own scans |
| `GET`  | `/api/scans/all` | Get all scans (doctor/admin) |
| `GET`  | `/api/scans/{id}` | Get single scan by ID |
| `PUT`  | `/api/scans/{id}/note` | Doctor saves review note |

### Doctor
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/doctor/patients` | List of DR patients with urgency flags |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/users/all` | All users |
| `POST` | `/api/users` | Create user |
| `PUT`  | `/api/users/{id}` | Update user |
| `DELETE` | `/api/users/{id}` | Delete user |
| `GET`  | `/api/doctors/all` | All doctors |
| `POST` | `/api/doctors` | Create/promote doctor |

### DevOps / MLOps
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/devops/stats` | Full monitoring stats: model metrics, user stats, system health, prediction logs |

### Chatbot
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat` | RAG-powered clinical Q&A |

---

## 🤖 AI Model Details

| Parameter | Value |
|-----------|-------|
| Architecture | EfficientNet-B0 (transfer learning) |
| Input size | 224 × 224 RGB |
| Output | Binary (DR / No DR) |
| Explainability | Grad-CAM heatmap overlay |
| Risk thresholds | Low < 50% · Medium 50–69% · High ≥ 70% |
| Urgent alert threshold | hasDR AND risk ≠ Low AND probability ≥ 85% |
| Dataset | APTOS 2019 Blindness Detection |

---

## 📊 MLOps Dashboard

Access at `/devops` — no login required. Shows:
- **Total predictions** and DR positive rate
- **Risk distribution** bar chart (Low / Medium / High)
- **Daily prediction volume** line chart (last 7 days)
- **System health**: model status, MongoDB connection, CPU / RAM / Disk gauges
- **User stats**: totals by role, new registrations this week
- **Recent prediction logs** table (anonymised)

Auto-refreshes every 30 seconds.

---

## 👥 Demo Accounts

| Role | Email | Password |
|------|-------|----------|
| Patient | `osmanibrahim6062@gmail.com` | `Password123!` |
| Doctor | `doctor@retinaguard.com` | `Password123!` |
| Admin | `admin@retinaguard.com` | `Password123!` |

> **Note:** Email verification bypass code: `123456` (works for any account during demo)

---

## 🐳 Deployment (VPS)

```bash
# Sync frontend build and backend to VPS
python sync_vps.py

# On VPS
docker-compose down && docker-compose up -d --build
docker ps   # verify both containers are healthy
```

---

## 📁 Project Structure

```
retinaguard-fastapi/
├── python-api/
│   ├── main.py              # FastAPI app + all endpoints
│   ├── auth_service.py      # JWT + password hashing
│   ├── database.py          # MongoDB Motor async client
│   ├── email_service.py     # Email verification (Brevo / SMTP)
│   ├── rag_service.py       # LangChain RAG chatbot
│   ├── config.py            # Settings / env vars
│   └── requirements.txt
├── docker-compose.yml
├── sync_vps.py              # One-command VPS deployment
└── README.md
```

---

## 📄 License

MIT © 2026 RetinalGuard Team — Graduation Project
