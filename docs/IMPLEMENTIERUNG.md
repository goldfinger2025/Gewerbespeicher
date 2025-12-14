# Implementierungs-Fahrplan

**Status:** Ready to build
**Tech-Lead:** Claude Opus 4.5

---

## Phase 1: MVP-Foundation

### Woche 1: Projekt Setup & Authentifizierung

#### Tag 1-2: Infrastruktur

**Accounts vorbereiten:**

- [ ] **Neon** (https://neon.tech) - PostgreSQL kostenlos
  - Database erstellen: `gewerbespeicher_dev`
  - Connection String speichern

- [ ] **Railway** (https://railway.app) - Backend Hosting
  - GitHub verbinden
  - Environment-Variablen konfigurieren

- [ ] **Vercel** (https://vercel.com) - Frontend Hosting
  - GitHub verbinden
  - Next.js Template

- [ ] **Anthropic API** (https://console.anthropic.com)
  - API Key generieren
  - Billing aktivieren

#### Tag 3-5: Frontend Initialisierung

```bash
cd frontend

# Dependencies installieren
npm install

# Development Server starten
npm run dev
```

#### Tag 6-7: Backend Initialisierung

```bash
cd backend

# Virtual Environment erstellen
python3.11 -m venv venv
source venv/bin/activate  # macOS/Linux

# Dependencies installieren
pip install -r requirements.txt

# Server starten
python main.py
```

**Test:**
```bash
curl http://localhost:8000/health
# → {"status": "healthy"}
```

---

### Woche 2: Database & Authentifizierung

#### Tag 1-3: PostgreSQL Setup

**Option A: Docker (empfohlen für Entwicklung)**
```bash
docker-compose up -d db
```

**Option B: Neon Dashboard**
```
https://console.neon.tech/
1. Neues Projekt: "gewerbespeicher"
2. Database: "gewerbespeicher_prod"
3. Connection String kopieren
```

**Schema initialisieren:**
```bash
# SQL-Datei ausführen
psql $DATABASE_URL < backend/init.sql
```

#### Tag 4-7: JWT Authentication

Implementierte Endpoints:
- `POST /api/v1/auth/login` - Login mit Email/Password
- `POST /api/v1/auth/register` - Neuer Benutzer
- `POST /api/v1/auth/refresh` - Token erneuern
- `GET /api/v1/auth/me` - Aktueller Benutzer

---

### Woche 3: Core Features

#### Simulation Engine

Die Simulation verwendet `pvlib` für PV-Ertragsberechnung:

```python
# Beispiel-Aufruf
POST /api/v1/simulate
{
    "project_id": "uuid",
    "pv_peak_power_kw": 100,
    "battery_capacity_kwh": 50,
    "annual_consumption_kwh": 150000
}
```

**Berechnete Metriken:**
- Autarkiegrad (%)
- Eigenverbrauchsquote (%)
- Jährliche Einsparungen (€)
- Amortisationszeit (Jahre)
- NPV und IRR

#### Komponenten-Datenbank

Vordefinierte Komponenten in `init.sql`:
- BYD Battery-Box Premium HVS 12.8
- Huawei LUNA2000-15-S0
- Fronius Symo GEN24 10.0 Plus
- Huawei SUN2000-50KTL-M3
- Trina Solar Vertex S+ 445W

---

### Woche 4: Angebotserstellung

#### KI-Angebote mit Claude

```python
# Claude Service
POST /api/v1/offers
{
    "simulation_id": "uuid",
    "generate_pdf": true
}
```

Claude erstellt automatisch:
- Professionelle Angebotsbeschreibung
- Technische Zusammenfassung
- ROI-Erklärung für Kunden

#### PDF-Generierung

Mit ReportLab wird ein professionelles PDF erstellt:
- Firmen-CI/Logo
- Simulationsergebnisse als Charts
- Komponentenliste
- Preisaufschlüsselung

---

## Phase 2: KI & Intelligenz

- [ ] Claude-basierte Optimierungsvorschläge
- [ ] Automatische Speicherdimensionierung
- [ ] Lastprofil-Analyse
- [ ] Wetterprognose-Integration

---

## Phase 3: Realwelt-Integration

- [ ] DocuSign E-Signatur
- [ ] HubSpot CRM-Sync
- [ ] Google Maps Satellitenbild
- [ ] PVGIS-Datenanbindung

---

## Phase 4: Enterprise Features ✅

### Multi-Tenant Support
- [x] Tenant-Model mit Subscription-Management
- [x] User-Rollen (Owner, Admin, Manager, User, Viewer)
- [x] Tenant-Isolation auf Datenbank-Ebene
- [x] Resource-Limits pro Tenant

### White-Label Option
- [x] Branding-Konfiguration (Logo, Farben, Fonts)
- [x] Custom Domain Support
- [x] Tenant-spezifische API-Endpoints
- [x] Public Branding Endpoint für Frontend

### Advanced Analytics
- [x] Tenant-weite Statistiken
- [x] User-Performance Metriken
- [x] Conversion Funnel Analytics
- [x] Perioden-Vergleiche
- [x] CSV-Export Funktion

### API für Drittanbieter
- [x] API-Key Management mit Scopes
- [x] Rate Limiting pro Key
- [x] IP-Whitelist Support
- [x] Key-Rotation (Regenerate)
- [x] Usage Tracking

---

## Quick Start Commands

```bash
# Gesamtes System starten
docker-compose up -d

# Nur Backend entwickeln
cd backend && python main.py

# Nur Frontend entwickeln
cd frontend && npm run dev

# Datenbank zurücksetzen
docker-compose down -v && docker-compose up -d db

# Logs anzeigen
docker-compose logs -f backend
```

---

## Environment Variables

Siehe `.env.example` Dateien in `/backend` und `/frontend`.
