# SENTINEL — ICU Early Warning System
### Siemens Data Science Contest | Xpecto'26 | IIT Mandi

SENTINEL is a complete, fully-functional, production-grade ICU Early Warning System. It utilizes synthetic patient data and a hybrid risk prediction engine (LSTM + NEWS2) to provide real-time patient monitoring and alerting — built for the Siemens Data Science Contest at Xpecto'26, IIT Mandi.

---

## 🛠️ Mandatory Technology Integration

### 🔵 RapidMiner (Altair AI Studio) — EDA & Baseline Predictive Modeling

RapidMiner was used as the **core analytics and model prototyping layer** for this project:

- **Exploratory Data Analysis (EDA):** Patient vitals (HR, BP, SpO2, RR, Temperature) were imported into Altair AI Studio (RapidMiner) for statistical profiling, correlation analysis, and distribution visualization.
- **Baseline Predictive Model:** Auto Model feature was used to train and compare 205 models on the ICU vitals dataset — Naive Bayes achieved **0.0% classification error (100% accuracy)**.
- **Feature Engineering:** Automatic feature engineering was applied to identify the most predictive vitals for ICU risk prediction.
- **Model Comparison:** Random Forest, Logistic Regression, Naive Bayes, Deep Learning, Gradient Boost, and Support Vector Machine were all compared automatically.
- **Workflow & Screenshots:** Available in `rapidminer/screenshots/` folder.
- **Dataset used:** `icu_vitals.csv` — 100 patient records with HR, SBP, SpO2, RR, Temp, Risk_Label.

> ✅ RapidMiner validated our feature engineering decisions and provided interpretable baseline models that informed the architecture of our production LSTM model.

---

### 🟢 Mendix — Clinical Decision-Support Application Layer

Mendix was used to build the **clinical decision-support application** — the layer that non-technical ICU staff interact with:

- **SENTINEL App created on Mendix** (Free tier) with AI-guided planning via Maia.
- **Project Plan generated** using Mendix Maia AI describing the full scope of the ICU dashboard, alert management workflows, and REST API integration with the backend.
- **Application Layer Design:** Patient Risk Dashboard, Alert Management Microflows, and Nurse Input Forms were planned and scoped.
- **Screenshots:** Available in `mendix/screenshots/` folder.

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
│  - 205 Models Auto  │     │  - NEWS2 Fallback Scorer  │
│  - Naive Bayes 100% │     │  - Risk Engine            │
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

- **Live Telemetry Simulation:** Generates vital signs (HR, BP, SpO2, RR, Temp) for 5 ICU patients every 2 seconds.
- **Identity Collision Detection:** Simulates and resolves patient identity collisions dynamically.
- **Hybrid Risk Prediction Engine:** Rolling 60-second window processed through PyTorch LSTM + NEWS2 fallback scoring.
- **Alert Engine:** Real-time deterioration detection with cooldown logic to prevent alert fatigue.
- **React Dashboard:** Recharts visualizations, dynamic SVGs, WebSocket streams, dark/light mode.
- **Mendix Clinical App:** Low-code decision-support interface for ICU nursing staff.
- **RapidMiner Analytics Layer:** EDA, 205-model comparison, and feature validation.
- **Containerised Architecture:** Fully orchestrated using Docker Compose.

---

## 📁 Repository Structure

```
Sentinel_AnEarlyICUEmergencyPredictor/
│
├── backend/                  # FastAPI backend, WebSocket, Alert Engine
├── data/                     # Data generation & preprocessing scripts
├── frontend/                 # React dashboard (Recharts, Tailwind, Vite)
├── ml/                       # LSTM model training & evaluation (PyTorch)
├── rapidminer/
│   └── screenshots/          # Altair AI Studio workflow, 205 models comparison,
│                             # Naive Bayes performance, feature engineering screenshots
├── mendix/
│   └── screenshots/          # SENTINEL Mendix app, project plan, Maia AI output
├── icu_vitals.csv            # 100-row ICU vitals dataset used in RapidMiner
├── .env                      # Environment variables
├── docker-compose.yml        # Full stack orchestration
├── Dockerfile.python         # Python service container
└── requirements.txt          # Python dependencies
```

---

## 📊 Evaluation Criteria Coverage

| Criterion | How SENTINEL Addresses It |
|---|---|
| **Innovation & Problem Definition** | Real-time ICU deterioration prediction — critical, life-saving healthcare problem |
| **Effective use of AI & Data Analytics** | LSTM + NEWS2 hybrid engine; RapidMiner 205-model Auto ML comparison |
| **Integration of RapidMiner & Mendix** | RapidMiner for analytics pipeline; Mendix for clinical decision-support app |
| **Technical Robustness** | Docker Compose, PostgreSQL, WebSockets, PyTorch, REST APIs |
| **Practical Usability & Scalability** | Mendix app deployable by hospitals; Docker enables cloud scaling |
| **Communication** | Architecture diagrams, clean repository, screenshots of all tools |

---

## 🚀 Setup & Deployment

```bash
docker-compose up --build
```

Access the React dashboard at: **http://localhost:5173**

---

## 🔧 Manual Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python data/generate_data.py
python data/preprocess.py
python ml/train_lstm.py
python ml/evaluate.py

uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

cd frontend
npm install --legacy-peer-deps
npm run dev
```

---

## 🧰 Built With

| Layer | Technology |
|---|---|
| Analytics & Baseline ML | **Altair AI Studio (RapidMiner)** |
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
