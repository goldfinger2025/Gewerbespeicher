# 🔋 Gewerbespeicher Planner

**KI-gestützte Planung und Angebotserstellung für PV-Speichersysteme**

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/EWS-GmbH/gewerbespeicher-app)
[![Tech Stack](https://img.shields.io/badge/stack-Next.js%2015%20%2B%20FastAPI%20%2B%20PostgreSQL-green.svg)]()
[![AI Powered](https://img.shields.io/badge/AI-Claude%20Opus%204.5-purple.svg)]()

---

## 🎯 Übersicht

Das Gewerbespeicher-Planungstool ermöglicht EWS-Installateurskunden die schnelle und präzise Konfiguration von PV-Speichersystemen für Gewerbeobjekte. Mit KI-gestützter Simulation und automatischer Angebotserstellung.

### Features

- ⚡ **Echtzeit-Simulation** - PV-Ertrag + Speicher-Logik mit pvlib
- 🤖 **KI-Angebote** - Automatische Angebotserstellung mit Claude Opus 4.5
- 📊 **Dashboard** - Visualisierung von Autarkiegrad, ROI und Einsparungen
- 📄 **PDF-Export** - Professionelle Angebots-PDFs
- ✍️ **E-Signatur** - DocuSign-Integration
- 🔗 **CRM-Integration** - HubSpot-Anbindung

---

## 🏗️ Architektur

```
┌──────────────────────────────────────────────────────────────────────┐
│                     FRONTEND (Next.js 15)                            │
│  Vercel Deployment                                                   │
│  ├─ /dashboard (Hauptseite)                                          │
│  ├─ /planner (Konfigurator)                                          │
│  ├─ /results (Simulationsergebnisse)                                 │
│  └─ /offers (Angebotsverwaltung)                                     │
└──────────────────────────────────────────────────────────────────────┘
                           ↕ HTTP/REST
┌──────────────────────────────────────────────────────────────────────┐
│                  BACKEND (Python FastAPI)                            │
│  Railway Deployment                                                  │
│  ├─ /api/v1/simulate (Speicher-Simulation)                          │
│  ├─ /api/v1/optimize (KI-Optimierung)                               │
│  ├─ /api/v1/offer (PDF-Generierung)                                 │
│  └─ /api/v1/components (Komponentendatenbank)                       │
└──────────────────────────────────────────────────────────────────────┘
                           ↕ SQL/Pools
┌──────────────────────────────────────────────────────────────────────┐
│               DATABASE (PostgreSQL + Redis)                          │
│  Neon (Serverless PostgreSQL) + Upstash (Redis)                     │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Schnellstart

### Voraussetzungen

- Node.js 20+
- Python 3.11+
- Docker (optional)
- PostgreSQL 16+

### 1. Repository klonen

```bash
git clone https://github.com/EWS-GmbH/gewerbespeicher-app.git
cd gewerbespeicher-app
```

### 2. Environment-Variablen

```bash
# Frontend
cp frontend/.env.example frontend/.env.local

# Backend
cp backend/.env.example backend/.env
```

### 3. Mit Docker starten (empfohlen)

```bash
docker-compose up -d
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000/docs
- PostgreSQL: localhost:5432

### 4. Oder manuell

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

---

## 📁 Projektstruktur

```
gewerbespeicher-app/
├── frontend/                 # Next.js 15 Frontend
│   ├── src/
│   │   ├── app/             # App Router
│   │   ├── components/      # React Komponenten
│   │   ├── hooks/           # Custom Hooks
│   │   ├── lib/             # Utilities
│   │   └── types/           # TypeScript Types
│   └── package.json
│
├── backend/                  # FastAPI Backend
│   ├── app/
│   │   ├── api/v1/          # API Endpoints
│   │   ├── core/            # Simulator, Optimizer
│   │   ├── services/        # Claude, PDF, CRM
│   │   └── models/          # SQLAlchemy Models
│   └── requirements.txt
│
├── shared/                   # Shared Types & Constants
├── docs/                     # Dokumentation
├── docker-compose.yml        # Docker Setup
└── README.md
```

---

## 🛠️ Tech Stack

### Frontend
- **Next.js 15** - React Framework mit App Router
- **TypeScript** - Type Safety
- **Tailwind CSS** - Styling
- **TanStack Query** - Data Fetching
- **Recharts** - Visualisierungen
- **Zod** - Schema Validation

### Backend
- **FastAPI** - Python Web Framework
- **SQLAlchemy 2.0** - ORM
- **pvlib** - PV-Simulation
- **Anthropic SDK** - Claude API
- **ReportLab** - PDF-Generierung

### Infrastructure
- **Vercel** - Frontend Hosting
- **Railway** - Backend Hosting
- **Neon** - PostgreSQL
- **Upstash** - Redis

---

## 📚 Dokumentation

- [Architektur](docs/ARCHITEKTUR.md) - Systemarchitektur und Tech-Stack Details
- [Implementierung](docs/IMPLEMENTIERUNG.md) - Setup-Anleitung und Fahrplan

### API Dokumentation

Nach dem Start verfügbar unter: http://localhost:8000/docs

### Hauptendpoints

| Endpoint | Method | Beschreibung |
|----------|--------|--------------|
| `/api/v1/projects` | GET/POST | Projekt-Management |
| `/api/v1/simulate` | POST | Simulation starten |
| `/api/v1/offers` | POST | Angebot generieren |
| `/api/v1/auth/login` | POST | Benutzer-Login |

---

## 🗓️ Roadmap

- [x] Phase 1: MVP Foundation (Wochen 1-4)
- [x] Phase 2: KI & Intelligenz (Wochen 5-8)
- [x] Phase 3: Realwelt-Integration (Wochen 9-12)
- [x] Phase 4: Enterprise Features (Wochen 13-16)

---

## 👥 Team

**EWS GmbH** - Handewitt, Germany

---

## 📄 Lizenz

MIT License - siehe [LICENSE](LICENSE)
