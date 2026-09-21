# RetinalGuard: AI-Powered Diabetic Retinopathy Detection

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-teal.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.16-orange.svg?logo=tensorflow)](https://www.tensorflow.org/)
[![React](https://img.shields.io/badge/React-18-blue.svg?logo=react)](https://react.dev/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An end-to-end clinical AI platform designed to assist healthcare professionals and patients in early screening of **Diabetic Retinopathy (DR)** from retinal fundus photographs. The platform combines deep learning classification with visual explainability (Explainable AI) and modern web technologies.

---

## Key Highlights

- **Deep Learning Screening**: Leverages fine-tuned EfficientNet-B0 architecture trained on fundus photography datasets for automated DR detection.
- **Explainable AI (Grad-CAM)**: Generates visual heatmaps highlighting suspicious retinal regions and microvascular lesions to support clinician decision-making.
- **Role-Based Portals**:
  - **Patient Portal**: Intuitive upload interface, AI-assisted diagnosis reports, and clinical guidance.
  - **Doctor Dashboard**: Prioritized patient review queue, risk stratification, and patient communication tools.
  - **Admin Console**: User access management and system-wide overview.
- **MLOps & Telemetry Dashboard**: Standalone monitoring view providing real-time model metrics, performance distribution, and infrastructure health telemetry.

---

## System Architecture

`
                       +------------------------+
                       |      Client / Web      |
                       |  (React 18 + TS + Vite)|
                       +-----------+------------+
                                   | (HTTP / JSON)
                                   v
                       +------------------------+
                       |   Nginx Reverse Proxy  |
                       +-----------+------------+
                                   |
         +-------------------------+-------------------------+
         |                                                   |
         v                                                   v
+------------------+                                +------------------+
|   Static Web     |                                |  FastAPI Backend |
|   Application    |                                |  (Python 3.10+)  |
+------------------+                                +--------+---------+
                                                             |
                                      +----------------------+----------------------+
                                      |                                             |
                                      v                                             v
                           +--------------------+                        +--------------------+
                           | TensorFlow / Keras |                        |   MongoDB Atlas    |
                           |  (EfficientNet-B0) |                        | (Cloud Datastore)  |
                           +--------------------+                        +--------------------+
`

---

## Technology Stack

- **Frontend**: React 18, TypeScript, Tailwind CSS, Vite, Lucide Icons, Recharts
- **Backend**: FastAPI, Uvicorn, Motor (Async MongoDB Driver), Pydantic
- **Deep Learning**: TensorFlow / Keras, NumPy, Pillow, SciPy, Matplotlib
- **Containerization & Deployment**: Docker, Docker Compose, Nginx

---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/)
- Python 3.10+ (for local backend development)
- Node.js 18+ (for local frontend development)

### 1. Clone the Repository

`ash
git clone https://github.com/lilosman/retinaguard-fastapi.git
cd retinaguard-fastapi
`

### 2. Environment Setup

Create a .env file in python-api/ using the template below:

`env
MONGO_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/retinaguard_db
JWT_SECRET=your_jwt_secret_key_here
MODEL_PATH=/app/output/efficientnetb0_blindness_model.keras
`

### 3. Run with Docker Compose

`ash
docker compose up --build -d
`

- Web Application: http://localhost
- API Documentation: http://localhost:8000/docs
- MLOps Telemetry: http://localhost/devops

---

## Project Structure

`
retinaguard-fastapi/
├── python-api/
│   ├── main.py              # Application entrypoint & route definitions
│   ├── auth_service.py      # Authentication & authorization logic
│   ├── database.py          # MongoDB connection management
│   ├── email_service.py     # Email notification services
│   ├── rag_service.py       # Clinical knowledge assistant services
│   ├── config.py            # Environment configuration
│   └── requirements.txt     # Python dependencies
├── docker-compose.yml       # Production container orchestration
└── README.md                # Project documentation
`

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Disclaimer

RetinalGuard is developed as an academic graduation project and clinical decision-support research tool. It is not intended to replace professional medical advice, clinical diagnosis, or treatment by a qualified ophthalmologist.
