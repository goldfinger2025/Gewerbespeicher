# Deployment Guide

Professionelle Deployment-Anleitung für den Gewerbespeicher Planner.

## Stack Overview

| Service | Plattform | Tier | Kosten |
|---------|-----------|------|--------|
| Frontend | Vercel | Pro | $20/Monat |
| Backend | Railway | Pro | $5-20/Monat |
| Database | Neon | Pro | $19/Monat |
| Cache | Upstash | Pro | $10/Monat |

---

## 1. Neon PostgreSQL Setup

### 1.1 Projekt erstellen

1. Gehe zu [console.neon.tech](https://console.neon.tech/)
2. Erstelle ein neues Projekt:
   - **Name**: `gewerbespeicher-prod`
   - **Region**: `eu-central-1` (Frankfurt)
   - **Postgres Version**: 16

### 1.2 Datenbank initialisieren

```bash
# Connection String kopieren (Format):
# postgresql://user:password@ep-xxx.eu-central-1.aws.neon.tech/gewerbespeicher?sslmode=require

# Schema importieren
psql $DATABASE_URL < backend/init.sql
```

### 1.3 Connection Pooling aktivieren

1. Settings > Connection Pooling > Enable
2. Pool Mode: `Transaction`
3. Pool Size: `10`

**Wichtig**: Verwende die Pooler-URL für die Anwendung:
```
postgresql://user:password@ep-xxx-pooler.eu-central-1.aws.neon.tech/gewerbespeicher?sslmode=require
```

---

## 2. Upstash Redis Setup

### 2.1 Datenbank erstellen

1. Gehe zu [console.upstash.com](https://console.upstash.com/)
2. Erstelle eine neue Redis-Datenbank:
   - **Name**: `gewerbespeicher-cache`
   - **Region**: `eu-central-1` (Frankfurt)
   - **TLS**: Aktiviert (Standard)

### 2.2 Connection String

```
# Format (TLS):
rediss://default:xxx@eu1-xxx.upstash.io:6379
```

---

## 3. Railway Backend Setup

### 3.1 Projekt erstellen

1. Gehe zu [railway.app](https://railway.app/)
2. "New Project" > "Deploy from GitHub repo"
3. Wähle `goldfinger2025/Gewerbespeicher`
4. Root Directory: `backend`

### 3.2 Environment Variables konfigurieren

Füge folgende Variablen hinzu:

```env
# Core
ENVIRONMENT=production
DEBUG=false
PORT=8000

# Database (Neon)
DATABASE_URL=postgresql://...@ep-xxx-pooler.eu-central-1.aws.neon.tech/gewerbespeicher?sslmode=require

# Cache (Upstash)
REDIS_URL=rediss://default:xxx@eu1-xxx.upstash.io:6379

# Auth (generiere mit: openssl rand -hex 32)
SECRET_KEY=your-64-char-secret-key

# AI API
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# CORS
ALLOWED_ORIGINS=https://your-app.vercel.app
```

### 3.3 Domain konfigurieren

1. Settings > Domains
2. Custom Domain: `api.gewerbespeicher.app`
3. SSL wird automatisch konfiguriert

---

## 4. Vercel Frontend Setup

### 4.1 Projekt importieren

1. Gehe zu [vercel.com](https://vercel.com/)
2. "Add New Project" > Import Git Repository
3. Wähle `goldfinger2025/Gewerbespeicher`
4. Root Directory: `frontend`
5. Framework Preset: Next.js

### 4.2 Environment Variables

```env
# Backend API
NEXT_PUBLIC_API_URL=https://api.gewerbespeicher.app
BACKEND_URL=https://api.gewerbespeicher.app

# Environment
NEXT_PUBLIC_ENVIRONMENT=production

# Optional: Maps
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=
```

### 4.3 Domain konfigurieren

1. Settings > Domains
2. Add: `gewerbespeicher.app`
3. SSL wird automatisch konfiguriert

---

## 5. GitHub Secrets konfigurieren

Für die CI/CD Pipeline werden folgende Secrets benötigt:

### Repository Settings > Secrets > Actions

```
# Vercel
VERCEL_TOKEN=xxx
VERCEL_ORG_ID=xxx
VERCEL_PROJECT_ID=xxx

# Railway
RAILWAY_TOKEN=xxx

# Database (für Migrations)
DATABASE_URL=postgresql://...

# Health Check URLs
BACKEND_URL=https://api.gewerbespeicher.app
FRONTEND_URL=https://gewerbespeicher.app
```

---

## 6. Erste Deployment

### 6.1 Manuelles Deployment testen

```bash
# Frontend (Vercel)
cd frontend
vercel --prod

# Backend (Railway)
cd backend
railway up
```

### 6.2 Datenbank-Migrationen

```bash
cd backend
alembic upgrade head
```

### 6.3 Health Checks

```bash
# Backend
curl https://api.gewerbespeicher.app/api/v1/health

# Frontend
curl -I https://gewerbespeicher.app
```

---

## 7. Monitoring & Logging

### 7.1 Vercel Analytics

1. Project Settings > Analytics > Enable
2. Web Vitals Dashboard verfügbar

### 7.2 Railway Logs

```bash
railway logs --service backend
```

### 7.3 Neon Monitoring

- Dashboard zeigt Query-Performance
- Connection usage tracking
- Storage metrics

### 7.4 Sentry (Optional)

```bash
# Frontend
npm install @sentry/nextjs

# Backend
pip install sentry-sdk[fastapi]
```

---

## 8. Backup & Recovery

### 8.1 Neon Automatic Backups

- Point-in-time recovery (PITR) für 7 Tage
- Branching für Staging-Umgebungen

### 8.2 Manueller Export

```bash
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

---

## 9. Scaling

### 9.1 Frontend (Vercel)

- Automatic scaling (serverless)
- Edge Functions für API routes

### 9.2 Backend (Railway)

```toml
# railway.toml
[deploy]
numReplicas = 2  # Horizontal scaling
```

### 9.3 Database (Neon)

- Autoscaling CPU: 0.25 - 4 vCPU
- Read replicas für Leselasten

---

## 10. Kosten-Übersicht (Pro Tier)

| Service | Plan | Kosten/Monat |
|---------|------|--------------|
| Vercel | Pro | $20 |
| Railway | Pro | ~$10-20 |
| Neon | Launch | $19 |
| Upstash | Pay-as-you-go | ~$5-10 |
| **Total** | | **~$55-70** |

---

## Checkliste vor Go-Live

- [ ] Neon Datenbank erstellt und Schema importiert
- [ ] Upstash Redis konfiguriert
- [ ] Railway Backend deployed und getestet
- [ ] Vercel Frontend deployed und getestet
- [ ] Custom Domains konfiguriert
- [ ] SSL-Zertifikate aktiv
- [ ] Environment Variables in allen Services gesetzt
- [ ] GitHub Secrets für CI/CD konfiguriert
- [ ] Health Checks erfolgreich
- [ ] Anthropic API Key funktioniert
- [ ] CORS richtig konfiguriert
- [ ] Backup-Strategie dokumentiert
