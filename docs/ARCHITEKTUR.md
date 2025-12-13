# Gewerbespeicher-Planungstool - Vollständige Architektur

**Version:** 1.0
**Datum:** Dezember 2025
**Status:** Production-Ready Architecture
**Tech-Stack:** Next.js 15 + FastAPI + PostgreSQL + Claude Opus 4.5

---

## Inhaltsverzeichnis

1. [Systemarchitektur](#systemarchitektur)
2. [Tech-Stack Details](#tech-stack-details)
3. [Database-Schema](#database-schema)
4. [API-Spezifikation](#api-spezifikation)
5. [Frontend-Komponenten](#frontend-komponenten)
6. [Backend-Module](#backend-module)
7. [Deployment-Strategie](#deployment-strategie)

---

## Systemarchitektur

### High-Level Übersicht

```
┌──────────────────────────────────────────────────────────────────────┐
│                     FRONTEND (Next.js 15)                            │
│  Vercel Deployment                                                   │
│  ├─ /app/dashboard (Hauptseite)                                      │
│  ├─ /app/planner (Konfigurator)                                      │
│  ├─ /app/results (Simulationsergebnisse)                             │
│  ├─ /app/offers (Angebotsverwaltung)                                 │
│  └─ /app/admin (Multi-Tenant Management)                             │
└──────────────────────────────────────────────────────────────────────┘
                           ↕ HTTP/REST
┌──────────────────────────────────────────────────────────────────────┐
│                  BACKEND (Python FastAPI)                            │
│  Railway Deployment                                                  │
│  ├─ /api/v1/simulate (Speicher-Simulation)                           │
│  ├─ /api/v1/optimize (KI-Optimierung)                                │
│  ├─ /api/v1/offer (PDF-Generierung)                                  │
│  ├─ /api/v1/components (Komponentendatenbank)                        │
│  ├─ /api/v1/auth (JWT Authentication)                                │
│  └─ /api/v1/webhooks (CRM-Integration)                               │
└──────────────────────────────────────────────────────────────────────┘
                           ↕ SQL/Pools
┌──────────────────────────────────────────────────────────────────────┐
│               DATABASE (PostgreSQL + Redis)                          │
│  Neon (Serverless PostgreSQL)                                        │
│  ├─ public.users (Benutzer-Management)                               │
│  ├─ public.projects (Anlageprojekte)                                 │
│  ├─ public.simulations (Rechenergebnisse)                            │
│  ├─ public.offers (Generierte Angebote)                              │
│  ├─ public.components (Komponentenkatalog)                           │
│  └─ public.leads (Lead-Management)                                   │
│                                                                      │
│  Redis (Upstash)                                                     │
│  ├─ Cache für Satellite-Imagery                                      │
│  ├─ Session Storage                                                  │
│  └─ Queue für PDF-Generierung                                        │
└──────────────────────────────────────────────────────────────────────┘
                           ↕ APIs
┌──────────────────────────────────────────────────────────────────────┐
│              EXTERNE SERVICES & DATENQUELLEN                         │
│  ├─ Anthropic Claude API (KI-Angebotserstellung)                     │
│  ├─ Google Maps API (Satellitenbild + Geo)                           │
│  ├─ Open-Meteo (Wetterdaten)                                         │
│  ├─ PVGIS (PV-Ertragsdaten)                                          │
│  ├─ DocuSign API (E-Signatur)                                        │
│  ├─ HubSpot API (CRM-Integration)                                    │
│  └─ BnA API (Netzgebühren)                                           │
└──────────────────────────────────────────────────────────────────────┘
```

### Datenfluss - Typical User Journey

```
1. KUNDEN-ERFASSUNG
   User → Lead-Form (Frontend)
   → Validierung → Database (projects)

2. AUTOMATISCHE STANDORT-ANALYSE
   Postleitzahl → Google Maps API
   → Satellite-Imagery + Wetterdaten (Open-Meteo)
   → Cache in Redis

3. SPEICHER-KONFIGURATION
   User zeichnet/konfiguriert → JSON an FastAPI Backend

4. SIMULATION
   FastAPI → pvlib-python + OpenEMS-Logic
   → Ergebnisse in DB (simulations)
   → Zu Frontend streamen (WebSocket)

5. KI-ANGEBOTSERSTELLUNG
   Simulation-Ergebnisse → Claude Opus 4.5 Prompt
   → Intelligente Angebots-Beschreibung
   → In DB speichern

6. PDF-GENERIERUNG
   Daten + Claude-Text → ReportLab
   → PDF mit Firma-CI
   → S3-Storage (optional)

7. KUNDENPORTAL
   Unique URL mit Angebot
   → E-Signatur (DocuSign)
   → CRM-Update (HubSpot)
   → Bestellbestätigung
```

---

## Tech-Stack Details

### Frontend (Next.js 15)

**Kerntechnologien:**

| Package | Version | Zweck |
|---------|---------|-------|
| next | 15.0+ | React Framework |
| react | 19+ | UI Library |
| typescript | 5.4+ | Type Safety |
| tailwindcss | 3.4+ | Styling |
| @tanstack/react-query | 5+ | Data Fetching |
| zod | 3.22+ | Validation |
| recharts | 2.10+ | Charts |
| axios | 1.7+ | HTTP Client |

**Ordnerstruktur:**

```
src/
├── app/
│   ├── (auth)/
│   │   ├── login/
│   │   └── register/
│   ├── dashboard/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── planner/
│   │   ├── offers/
│   │   └── settings/
│   └── layout.tsx
├── components/
│   ├── ui/
│   ├── forms/
│   ├── visualizations/
│   └── common/
├── hooks/
├── lib/
└── types/
```

### Backend (FastAPI)

**Kerntechnologien:**

| Package | Version | Zweck |
|---------|---------|-------|
| fastapi | 0.115+ | Web Framework |
| sqlalchemy | 2.0+ | ORM |
| pydantic | 2.6+ | Validation |
| anthropic | 0.39+ | Claude API |
| pvlib | 0.10+ | PV Simulation |
| reportlab | 4.2+ | PDF Generation |

**Ordnerstruktur:**

```
app/
├── api/
│   └── v1/
│       ├── router.py
│       └── endpoints/
│           ├── auth.py
│           ├── projects.py
│           ├── simulations.py
│           ├── offers.py
│           └── components.py
├── core/
│   └── simulator.py
├── services/
│   └── claude_service.py
├── models/
├── crud/
└── utils/
```

---

## Database-Schema

### Haupttabellen

| Tabelle | Beschreibung |
|---------|--------------|
| `users` | Benutzer und Authentifizierung |
| `projects` | Kundenprojekte mit PV/Speicher-Konfiguration |
| `simulations` | Simulationsergebnisse und Metriken |
| `offers` | Generierte Angebote mit PDF und E-Signatur |
| `components` | Komponentenkatalog (Batterien, Wechselrichter, Module) |
| `audit_log` | Änderungsprotokoll |

### Entity-Relationship

```
users (1) ──────< projects (n)
                      │
                      └──────< simulations (n)
                                    │
                                    └──────< offers (n)
```

---

## API-Spezifikation

### Hauptendpoints

| Endpoint | Method | Beschreibung |
|----------|--------|--------------|
| `/api/v1/auth/login` | POST | JWT Login |
| `/api/v1/auth/register` | POST | Benutzerregistrierung |
| `/api/v1/projects` | GET/POST | Projekt-Management |
| `/api/v1/projects/{id}` | GET/PATCH/DELETE | Einzelnes Projekt |
| `/api/v1/simulate` | POST | Simulation starten |
| `/api/v1/simulations/{id}` | GET | Simulationsergebnis |
| `/api/v1/offers` | POST | Angebot generieren |
| `/api/v1/offers/{id}` | GET | Angebot abrufen |
| `/api/v1/offers/{id}/pdf` | GET | PDF Download |
| `/api/v1/components` | GET | Komponentenkatalog |
| `/api/v1/optimize` | POST | KI-Optimierung |
| `/health` | GET | Health Check |

---

## Deployment-Strategie

### Entwicklung (Local)

```bash
docker-compose up -d
# Frontend: http://localhost:3000
# Backend: http://localhost:8000/docs
# PostgreSQL: localhost:5432
# Redis: localhost:6379
# Adminer: http://localhost:8080
```

### Produktion

| Service | Provider | URL |
|---------|----------|-----|
| Frontend | Vercel | gewerbespeicher.app |
| Backend | Railway | api.gewerbespeicher.app |
| Database | Neon | (Serverless PostgreSQL) |
| Cache | Upstash | (Serverless Redis) |

---

## Sicherheit

- JWT-basierte Authentifizierung
- CORS-Middleware mit Whitelist
- Rate Limiting
- SQL Injection Protection (SQLAlchemy ORM)
- Environment Variables für Secrets
- HTTPS-only in Produktion
