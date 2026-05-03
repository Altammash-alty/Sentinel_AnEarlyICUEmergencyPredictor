# SENTINEL — ICU Early Warning System
### Siemens Data Science Contest | Xpecto'26 | IIT Mandi

SENTINEL is a complete, fully-functional, production-grade ICU Early Warning System. It utilizes synthetic patient data and a hybrid risk prediction engine (LSTM + NEWS2) to provide real-time patient monitoring and alerting — built for the Siemens Data Science Contest at Xpecto'26, IIT Mandi.

---

## 🛠️ Mandatory Technology Integration

### 🔵 RapidMiner — EDA & Baseline Predictive Modeling
RapidMiner was used as the **core analytics and model prototyping layer** for this project:

- **Exploratory Data Analysis (EDA):** Patient vitals (HR, BP, SpO2, RR, Temperature) were imported into RapidMiner for statistical profiling, correlation analysis, and distribution visualization.
- **Baseline Predictive Model:** A Random Forest classifier was trained in RapidMiner on the preprocessed ICU vitals dataset to predict patient deterioration risk (Low / Medium / High / Critical).
- **Feature Importance:** RapidMiner's Weight by Information Gain operator was used to identify the most predictive vitals — SpO2 and Respiratory Rate emerged as top predictors.
- **Model Comparison:** RapidMiner's Auto Model feature was used to benchmark Logistic Regression, Decision Tree, and Random Forest — Random Forest achieved the highest AUC (0.94).
- **Workflow Export:** The full RapidMiner workflow is saved as `sentinel_icu_workflow.rmp` and screenshots are available in the root folder of the repository.

> ✅ RapidMiner validated our feature engineering decisions and provided interpretable baseline models that informed the architecture of our production LSTM model.

---

### 🟢 Mendix — Decision-Support Application Layer
Mendix was used to build the **clinical decision-support interface** — the application layer that non-technical ICU staff interact with:

- **Patient Risk Dashboard:** A Mendix page displays real-time risk scores per patient, color-coded by severity (Green/Amber/Red).
- **Alert Management Workflow:** Microflows handle incoming alert events and route them to the appropriate nurse station.
- **Decision-Support Input Form:** Clinicians can manually input patient vitals and receive an instant risk prediction via the integrated model API.
- **Mendix ↔ Backend Integration:** REST API connectors link the Mendix app to the FastAPI backend, enabling live data pull every 30 seconds.
- **Screenshots & prototype:** Available in the root folder of the repository.

> ✅ Mendix provides the scalable, low-code application layer that makes SENTINEL deployable in real hospital environments without requiring frontend engineering resources.

---

## 🏗️ Full System Architecture

```
Raw Vitals Stream
       │
       ▼
┌─────────────────────┐     ┌──────────────────────────┐
│   RapidMiner        │     │   Python ML Pipeline     │
│  - EDA & Profiling  │────▶│  - LSTM (PyTorch)        │
│  - Baseline Models  │     │  - NEWS2 Fallback Scorer  │
│  - Feature Selection│     │  - Risk Engine            │
└─────────────────────┘     └────────────┬─────────────┘
                                         │
                                         ▼
                             ┌──────────────────────────┐
                             │   FastAPI Backend         │
                             │  - REST API               │
                             │  - WebSocket Streams      │
                             │  - Alert Engine           │
                             └────────┬─────────────────┘
                                      │
                   ┌──────────────────┴──────────────────┐
                   ▼                                      ▼
     ┌─────────────────────┐              ┌──────────────────────────┐
     │   React Dashboard   │              │   Mendix Application     │
     │  - Live Telemetry   │              │  - Clinical Decision UI  │
     │  - Alert Feed       │              │  - Alert Workflows       │
     │  - Risk Charts      │              │  - REST Integration      │
     └─────────────────────┘              └──────────────────────────┘
```

---

## ✨ Features

- **Live Telemetry Simulation**: Generates vital signs (HR, BP, SpO2, RR, Temp) for 5 ICU patients every 2 seconds.
- **Identity Collision Detection**: Simulates and resolves patient identity collisions dynamically.
- **Hybrid Risk Prediction Engine**: Rolling 60-second window processed through PyTorch LSTM + NEWS2 fallback scoring.
- **Alert Engine**: Real-time deterioration detection with cooldown logic to prevent alert fatigue.
- **React Dashboard**: Recharts visualizations, dynamic SVGs, WebSocket streams, dark/light mode.
- **Mendix Clinical App**: Low-code decision-support interface for ICU nursing staff.
- **RapidMiner Analytics Layer**: EDA, baseline modeling, and feature validation.
- **Containerised Architecture**: Fully orchestrated using Docker Compose.

---

## 📁 Repository Structure

```
Sentinel_AnEarlyICUEmergencyPredictor/
│
├── backend/              # FastAPI backend, WebSocket, Alert Engine
├── data/                 # Data generation & preprocessing scripts
├── frontend/             # React dashboard (Recharts, Tailwind, Vite)
├── ml/                   # LSTM model training & evaluation (PyTorch)
├── icu_vitals.csv        # ICU patient vitals dataset (RapidMiner input)
├── sentinel_icu_workflow.rmp  # RapidMiner/AI Studio workflow file
├── [screenshots]         # RapidMiner & Mendix screenshots (root folder)
├── .env                  # Environment variables
├── docker-compose.yml    # Full stack orchestration
├── Dockerfile.python     # Python service container
└── requirements.txt      # Python dependencies
```

---

## 🚀 Setup & Deployment (Recommended)

The easiest way to run the full stack is via Docker Compose:

```bash
docker-compose up --build
```

> On first run: generates 10,000 patient sequences → preprocesses → trains LSTM → starts FastAPI + React frontend.

Access the React dashboard at: **http://localhost:5173**

---

## 🔧 Manual Setup (Development Mode)

### 1. Database
Ensure PostgreSQL or TimescaleDB is running. Set credentials in `.env`.

### 2. Python Environment
```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. ML Pipeline
```bash
python data/generate_data.py
python data/preprocess.py
python ml/train_lstm.py
python ml/evaluate.py
```

### 4. Backend
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Frontend
```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

---

## 📊 Evaluation Criteria Coverage

| Criterion | How SENTINEL Addresses It |
|---|---|
| **Innovation & Problem Definition** | Real-time ICU deterioration prediction — a critical, high-impact healthcare problem |
| **Effective use of AI & Data Analytics** | LSTM + NEWS2 hybrid engine; RapidMiner EDA & baseline modeling |
| **Integration of RapidMiner & Mendix** | RapidMiner for analytics pipeline; Mendix for clinical decision-support app |
| **Technical Robustness** | Docker Compose, PostgreSQL, WebSockets, PyTorch, REST APIs |
| **Practical Usability & Scalability** | Mendix app deployable by hospitals; Docker enables cloud scaling |
| **Communication** | Architecture diagrams, video demo, clean repository structure |

---

## 🏆 Innovation Highlights

1. **Hybrid Scoring**: LSTM handles temporal patterns; NEWS2 ensures clinical validity when data is sparse — no single point of failure.
2. **Identity Collision Resolver**: Handles real-world ICU scenario where patient wristband data may conflict.
3. **Alert Fatigue Prevention**: Cooldown logic ensures nurses aren't overwhelmed by repeated alerts for the same patient.
4. **Two-Layer Architecture**: RapidMiner (analytics/research layer) + Mendix (clinical deployment layer) mirrors how real hospital IT systems are structured.

---

## 🧰 Built With

| Layer | Technology |
|---|---|
| Analytics & Baseline ML | **RapidMiner Studio** |
| Clinical App | **Mendix** |
| ML Production Model | PyTorch (LSTM), Scikit-Learn |
| Backend | FastAPI, WebSockets |
| Database | PostgreSQL, TimescaleDB |
| Frontend | React, Recharts, Tailwind CSS, Vite |
| Infrastructure | Docker, Docker Compose |

---

## 👤 Author

**Altamash** | mdaltamashzzama@gmail.com
Submitted for: **Siemens Data Science Contest — Xpecto'26, IIT Mandi**
