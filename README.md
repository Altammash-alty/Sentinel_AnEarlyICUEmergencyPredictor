# SENTINEL — ICU Early Warning System

SENTINEL is a complete, fully-functional, production-grade ICU Early Warning System. It utilizes synthetic patient data and a hybrid risk prediction engine (LSTM + NEWS2) to provide real-time patient monitoring and alerting.

## Features

- **Live Telemetry Simulation**: Generates vital signs (HR, BP, SpO2, RR, Temp) for 5 ICU patients every 2 seconds.
- **Identity Collision Detection**: Simulates and resolves patient identity collisions dynamically.
- **Risk Prediction Engine**: Maintains a rolling window of vitals, evaluates risk using a PyTorch LSTM model, and falls back to NEWS2 if data is insufficient.
- **Alert Engine**: Real-time evaluation of patient deterioration with cooldowns to prevent alert fatigue.
- **Modern Dashboard**: A complete React interface featuring Recharts, dynamic SVGs, WebSocket streams, and a comprehensive dark/light mode UI.
- **Containerised Architecture**: Fully orchestrated using Docker Compose.

## System Prerequisites

- Docker
- Docker Compose
- Node.js & npm (if running frontend locally outside Docker)
- Python 3.11 (if running backend locally outside Docker)

## Setup & Deployment (Recommended)

The easiest way to run the full stack is via Docker Compose. It automatically wires the database, data generation, ML training, backend API, and frontend.

1. Ensure the Docker daemon is running.
2. Build and start the containers:
   ```bash
   docker-compose up --build
   ```
   *Note: On the first run, the system will generate 10,000 patient sequences, preprocess them, train the LSTM model, and then spin up the FastAPI backend and React frontend.*

3. Access the dashboard:
   Open your browser and navigate to: **http://localhost:5173**

## Manual Setup (Development Mode)

If you prefer to run the services individually:

### 1. Database
Ensure you have a PostgreSQL or TimescaleDB instance running. Set the credentials in `.env`.

### 2. Python Environment
Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Machine Learning Pipeline
Generate data and train the model:
```bash
python data/generate_data.py
python data/preprocess.py
python ml/train_lstm.py
python ml/evaluate.py
```

### 4. Backend
Start the FastAPI application:
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Frontend
Install necessary packages and start the Vite development server:
```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

## Architecture Flow

1. `simulator.py` generates hex packets containing vitals and patient IDs.
2. `identity_resolver.py` checks for inconsistencies against rolling baselines.
3. `risk_engine.py` processes 60-second windows through the LSTM model + NEWS2 scoring.
4. `alert_engine.py` monitors for critical vitals and triggers REST/WS alerts.
5. All data is persisted to PostgreSQL running via docker.
6. The React Dashboard manages 4 distinct WebSocket connections for live rendering.

## Built With
- FastAPI & WebSockets
- PyTorch & Scikit-Learn
- React, Recharts & Tailwind CSS
- PostgreSQL & TimescaleDB
