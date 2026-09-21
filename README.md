# 🔬 RetinalGuard

<p align="center">
  <strong>An Intelligent Clinical Decision-Support System for Automated Diabetic Retinopathy Screening</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Active-success.svg?style=flat-square" alt="Status" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688.svg?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/TensorFlow-2.16-FF6F00.svg?style=flat-square&logo=tensorflow&logoColor=white" alt="TensorFlow" />
  <img src="https://img.shields.io/badge/React-18-61DAFB.svg?style=flat-square&logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/MongoDB-Atlas-47A248.svg?style=flat-square&logo=mongodb&logoColor=white" alt="MongoDB" />
  <img src="https://img.shields.io/badge/Docker-Enabled-2496ED.svg?style=flat-square&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square" alt="License" />
</p>

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Key Capabilities](#-key-capabilities)
- [System Architecture](#-system-architecture)
- [Technology Stack](#-technology-stack)
- [API Reference](#-api-reference)
- [AI Model & Explainability](#-ai-model--explainability)
- [Getting Started](#-getting-started)
- [Repository Structure](#-repository-structure)
- [Medical Disclaimer & License](#-medical-disclaimer--license)

---

## 🌐 Overview

**RetinalGuard** is an end-to-end clinical AI platform designed to facilitate early screening and triage of **Diabetic Retinopathy (DR)** from digital retinal fundus images.

Diabetic Retinopathy is one of the leading causes of preventable visual impairment worldwide. RetinalGuard combines deep learning classification with transparent visual evidence to assist clinicians and patients:

- **Automated Screening**: Fast classification of fundus images using deep transfer learning.
- **Explainable Diagnostics**: Visual heatmaps highlighting pathological lesions (hemorrhages, exudates) to explain model predictions.
- **Coordinated Care**: Integrated roles for patients, ophthalmologists, and system administrators.
- **MLOps Telemetry**: Standalone monitoring dashboard providing real-time metrics on model predictions, risk distributions, and system health.

---

## ✨ Key Capabilities

| Capability | Architecture | Clinical Benefit |
|---|---|---|
| **AI Screening** | Deep Transfer Learning (EfficientNet-B0) | Instant binary classification with probability scoring |
| **Explainable AI (XAI)** | Gradient-weighted Class Activation Mapping (Grad-CAM) | Highlights suspicious retinal vascular anomalies |
| **Urgent Triage** | Clinical risk stratification engine ($\ge 85\%$ threshold) | Flags high-risk cases for prioritized ophthalmologist follow-up |
| **Patient Portal** | Responsive React dashboard | Simple scan uploads, historical reports, and clinical guidance |
| **Doctor Review** | Prioritized patient directory | Direct access to urgent cases with diagnostic review tools |
| **MLOps Telemetry** | Standalone `/devops` monitoring view | Real-time tracking of model traffic, risk trends, and server load |

---

## 🏗️ System Architecture

RetinalGuard uses a containerized, decoupled client-server architecture:

```text
┌─────────────────────────────────────────────────────────────┐
│                       Client Tier                           │
│  React 18 SPA · TypeScript · Vite · Tailwind CSS · Recharts │
└──────────────────────────────┬──────────────────────────────┘
                               │ (HTTP / JSON over Port 80)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                      Nginx Reverse Proxy                    │
│   Serves Static Assets · Proxies /api/ Requests · Gzip      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     Application Tier                        │
│          FastAPI (Python 3.10+) · Uvicorn Engine            │
│   Auth & RBAC · Async I/O · ThreadPool Model Execution      │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
               ▼                               ▼
┌─────────────────────────────┐ ┌─────────────────────────────┐
│       AI Pipeline Tier      │ │        Database Tier        │
│   TensorFlow / Keras Engine │ │    MongoDB Atlas Cluster    │
│ EfficientNet-B0 + Grad-CAM  │ │   Users · Scans Collection  │
└─────────────────────────────┘ └─────────────────────────────┘
```

---

## 🛠️ Technology Stack

- **Core Backend**: FastAPI, Uvicorn, Pydantic, Python-Jose (JWT), Passlib (Bcrypt)
- **Deep Learning & Imaging**: TensorFlow 2.16, Keras, NumPy, Pillow, SciPy, Matplotlib
- **Frontend & UI**: React 18, TypeScript, Tailwind CSS, Vite, Lucide Icons, Recharts
- **Database**: MongoDB Atlas via Motor (Async Python Driver)
- **DevOps & Containerization**: Docker, Docker Compose, Nginx, psutil

---

## 📡 API Reference

Interactive OpenAPI documentation is automatically served at `/docs` when the backend is running.

### Authentication & Profiles
| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| `POST` | `/api/auth/register` | Public | Register a new user account |
| `POST` | `/api/auth/login` | Public | Authenticate user and issue JWT token |
| `POST` | `/api/auth/verify-email` | Public | Email verification workflow |
| `POST` | `/api/auth/google` | Public | Social authentication flow |

### Clinical Screening & Diagnostic Records
| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| `POST` | `/predict` | Authorized | Submit retinal scan for AI inference & Grad-CAM |
| `GET` | `/api/scans/my` | Patient | Retrieve scan history for authenticated patient |
| `GET` | `/api/doctor/patients` | Doctor | Retrieve prioritized list of active DR cases |
| `PUT` | `/api/scans/{id}/note` | Doctor | Attach specialist diagnosis and review notes |

### Telemetry & MLOps
| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| `GET` | `/api/devops/stats` | Telemetry | System health, model telemetry, risk distribution |
| `GET` | `/health` | Public | Service health probe |

---

## 🧠 AI Model & Explainability

- **Architecture**: EfficientNet-B0 (Compound Scaling method)
- **Input Dimensions**: $224 	imes 224 	imes 3$ (RGB)
- **Classification Output**: Binary diagnosis with probability distribution
- **Explainability**: Grad-CAM calculates gradients of the score with respect to feature maps of the final convolutional layer (`top_conv`), generating an overlaid visual heatmap.

### Clinical Triage Logic
- **Low Risk**: Probability $< 30\%$ or non-pathological finding.
- **Medium Risk**: Probability between $30\%$ and $69\%$.
- **High Risk / Urgent**: Positive DR finding with probability $\ge 85\%$, automatically escalating to priority specialist review.

---

## 🚀 Getting Started

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/)
- Python 3.10+ (for local backend development)
- Node.js 18+ (for local frontend development)

### 1. Clone the Repository
```bash
git clone https://github.com/lilosman/retinaguard-fastapi.git
cd retinaguard-fastapi
```

### 2. Configure Environment
Create a `.env` file in the `python-api/` directory:
```env
MONGO_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/retinaguard_db
JWT_SECRET=your_secure_jwt_secret_key
MODEL_PATH=/app/output/efficientnetb0_blindness_model.keras
```

### 3. Start Containers
```bash
docker compose up --build -d
```

### 4. Access the Application
- **Web Application**: `http://localhost`
- **Interactive API Docs**: `http://localhost:8000/docs`
- **MLOps Telemetry**: `http://localhost/devops`

---

## 📂 Repository Structure

```text
retinaguard-fastapi/
├── python-api/
│   ├── main.py              # Application entrypoint & REST endpoints
│   ├── auth_service.py      # Authentication & authorization handlers
│   ├── database.py          # MongoDB asynchronous client
│   ├── email_service.py     # Verification & email services
│   ├── rag_service.py       # Clinical Q&A assistance pipeline
│   ├── config.py            # Environment configuration
│   └── requirements.txt     # Python backend dependencies
├── docker-compose.yml       # Container composition specification
├── .gitignore               # Ignored build and credential artifacts
└── README.md                # Project documentation
```

---

## ⚖️ Medical Disclaimer & License

### Medical Disclaimer
RetinalGuard is developed as an **academic graduation project and clinical decision-support research tool**. It is intended to assist medical professionals and is not certified as an independent medical device. All diagnostic findings must be clinically evaluated and confirmed by a certified ophthalmologist.


