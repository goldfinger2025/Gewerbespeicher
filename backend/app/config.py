"""
Application Configuration
Uses pydantic-settings for environment variable management
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union
from functools import lru_cache


class Settings(BaseSettings):
    """Application Settings loaded from environment variables"""

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/gewerbespeicher"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # JWT Authentication
    # SECURITY: SECRET_KEY must be set via environment variable in production
    # Generate a secure key with: openssl rand -hex 32
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION-USE-OPENSSL-RAND-HEX-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @field_validator("SECRET_KEY", mode="after")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Ensure SECRET_KEY is not the default in production"""
        import warnings
        import os
        if "CHANGE-ME" in v or "your-super-secret" in v:
            env = os.getenv("ENVIRONMENT", "development")
            if env == "production":
                raise ValueError(
                    "CRITICAL: SECRET_KEY must be set via environment variable in production! "
                    "Generate with: openssl rand -hex 32"
                )
            warnings.warn(
                "Using default SECRET_KEY - set via environment variable for production",
                UserWarning
            )
        return v

    # API Keys
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_MAPS_API_KEY: str = ""

    # CORS - accepts comma-separated string or list
    ALLOWED_ORIGINS: Union[str, List[str]] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://gewerbespeicher.app",
        "https://gewerbespeicher.vercel.app",
    ]

    # Production domains that should ALWAYS be allowed (merged with ALLOWED_ORIGINS)
    _REQUIRED_ORIGINS: List[str] = [
        "https://gewerbespeicher.vercel.app",
        "https://gewerbespeicher.app",
        "https://www.gewerbespeicher.app",
        "https://gewerbespeicher-production.up.railway.app",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string or list and merge with required origins"""
        # Parse input
        if isinstance(v, str):
            origins = [origin.strip() for origin in v.split(",") if origin.strip()]
        else:
            origins = v if v else []

        # Always include required production origins
        required = [
            "https://gewerbespeicher.vercel.app",
            "https://gewerbespeicher.app",
            "https://www.gewerbespeicher.app",
            "https://gewerbespeicher-production.up.railway.app",
        ]

        # Merge and deduplicate
        all_origins = list(set(origins + required))
        return all_origins

    # External Services - Phase 3 Integrations
    HUBSPOT_API_KEY: str = ""
    HUBSPOT_PORTAL_ID: str = ""

    DOCUSIGN_API_KEY: str = ""
    DOCUSIGN_ACCOUNT_ID: str = ""
    DOCUSIGN_USER_ID: str = ""
    DOCUSIGN_PRIVATE_KEY: str = ""
    DOCUSIGN_WEBHOOK_SECRET: str = ""
    DOCUSIGN_PRODUCTION: bool = False

    # Frontend URL for callbacks
    FRONTEND_URL: str = "http://localhost:3000"

    # PV Simulation Defaults
    DEFAULT_ELECTRICITY_PRICE: float = 0.30  # EUR/kWh
    DEFAULT_FEED_IN_TARIFF: float = 0.0786  # EUR/kWh (Stand 08/2025 für ≤10 kWp Teileinspeisung)
    DEFAULT_PV_TILT: float = 30.0  # degrees
    DEFAULT_PV_ORIENTATION: str = "south"

    # Germany Coordinates (for default location)
    DEFAULT_LATITUDE: float = 54.5  # Handewitt area
    DEFAULT_LONGITUDE: float = 9.3


# =============================================================================
# GEWERBESPEICHER KONSTANTEN (Stand: Dezember 2025)
# =============================================================================

# EEG Einspeisevergütung (Stand 08/2025, halbjährliche Degression -1%)
# Quelle: https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/ErneuerbareEnergien/EEG_Foerderung/start.html
EEG_FEED_IN_TARIFFS = {
    "teileinspeisung": {
        "bis_10kwp": 0.0786,     # 7,86 ct/kWh
        "10_40kwp": 0.0680,      # 6,80 ct/kWh
        "40_100kwp": 0.0680,     # 6,80 ct/kWh (Solarpaket I +1,5ct ausstehend)
        "ueber_100kwp": 0.0680,  # Direktvermarktung empfohlen
    },
    "volleinspeisung": {
        "bis_10kwp": 0.1247,     # 12,47 ct/kWh
        "10_40kwp": 0.1045,      # 10,45 ct/kWh
        "40_100kwp": 0.1045,
    },
    "degression_prozent": 0.01,  # -1% alle 6 Monate
    "naechste_degression": "2026-02-01",
    "stand": "2025-08-01",
    "gueltig_bis": "2026-01-31",
}

# Investitionskosten 2025 (Gewerbe, inkl. Installation)
# Preise basieren auf aktuellen Marktdaten
INVESTMENT_COSTS_2025 = {
    "pv_cost_per_kwp": {
        "bis_30kwp": 1200,       # €/kWp (Kleinanlagen)
        "30_100kwp": 1050,       # €/kWp (mittlere Gewerbe)
        "100_500kwp": 950,       # €/kWp (größere Gewerbe)
        "ueber_500kwp": 850,     # €/kWp (Industrie)
    },
    "battery_cost_per_kwh": {
        "bis_30kwh": 700,        # €/kWh (kleine Speicher)
        "30_100kwh": 600,        # €/kWh (mittlere Speicher)
        "100_500kwh": 520,       # €/kWh (große Gewerbespeicher)
        "ueber_500kwh": 450,     # €/kWh (Industriespeicher)
    },
    "fixed_costs": {
        "planung": 1500,         # Projektplanung
        "anmeldung": 500,        # Netzanmeldung, MaStR
        "inbetriebnahme": 1000,  # Inbetriebnahme, Dokumentation
    },
    "installation_factor": 0.10,  # 10% der Komponentenkosten
}

# Leistungspreise für Netzentgelte (regional sehr unterschiedlich!)
# Relevant ab 100.000 kWh/Jahr (RLM-Messung)
LEISTUNGSPREISE_EUR_KW_JAHR = {
    "niedrig": 60,              # €/kW/Jahr (ländlich, kleine EVU)
    "mittel": 100,              # €/kW/Jahr (Durchschnitt)
    "hoch": 150,                # €/kW/Jahr (städtisch)
    "sehr_hoch": 250,           # €/kW/Jahr (Ballungsräume)
    "extrem": 440,              # €/kW/Jahr (Spitzennetze)
    "default": 100,             # Standardwert für Berechnungen
}

# Netzentgelt-Schwellenwerte
NETZENTGELT_SCHWELLEN = {
    "rlm_messung_ab_kwh": 100000,      # Ab 100 MWh/Jahr: Leistungsmessung
    "individuell_ab_kwh": 10000000,    # Ab 10 GWh/Jahr: individuelle Netzentgelte
    "vollbenutzungsstunden_rabatt": {
        7000: 0.20,  # 20% Rabatt ab 7000 h
        7500: 0.30,  # 30% Rabatt ab 7500 h
        8000: 0.40,  # 40% Rabatt ab 8000 h
    }
}

# §14a EnWG - Steuerbare Verbrauchseinrichtungen (ab 01.01.2024)
PARA_14A_ENWG = {
    "schwelle_kw": 4.2,         # Speicher > 4,2 kW betroffen
    "module": {
        "modul1": {
            "name": "Pauschale Erstattung",
            "beschreibung": "Jährliche pauschale Vergütung",
            "erstattung_min": 110,   # €/Jahr
            "erstattung_max": 190,   # €/Jahr
            "erstattung_default": 150,
            "voraussetzung": "Steuerbarkeit durch Netzbetreiber",
        },
        "modul2": {
            "name": "Reduziertes Netzentgelt",
            "beschreibung": "60% Rabatt auf Netzentgelt",
            "rabatt_prozent": 0.60,
            "voraussetzung": "Separater Zähler erforderlich",
        },
        "modul3": {
            "name": "Zeitvariables Netzentgelt",
            "beschreibung": "Dynamische Netzentgelte nach Netzauslastung",
            "verfuegbar_ab": "2025-04-01",
            "voraussetzung": "Smart Meter (iMSys) erforderlich",
        }
    },
    "uebergangsfrist_bestand": "2028-12-31",
}

# Förderungen (Stand Dezember 2025)
FOERDERUNGEN = {
    "bund": {
        "kfw_270": {
            "name": "KfW 270 - Erneuerbare Energien Standard",
            "typ": "Kredit",
            "max_finanzierung": 1.0,  # 100%
            "laufzeit_min": 5,
            "laufzeit_max": 30,
            "effektivzins_ab": 3.66,  # Stand 12/2025
            "tilgungsfreie_jahre": 2,
            "antragstellung": "Vor Bestellung bei Hausbank",
            "url": "https://www.kfw.de/270",
            "aktiv": True,
        },
        "mwst_befreiung": {
            "name": "Mehrwertsteuerbefreiung (§12 Abs. 3 UStG)",
            "typ": "Steuerersparnis",
            "bedingung_kwp_max": 30,
            "ersparnis_prozent": 0.19,
            "automatisch": True,
            "aktiv": True,
        }
    },
    "laender": {
        "BW": {
            "name": "Baden-Württemberg",
            "programm": "Netzdienliche PV-Speicher",
            "aktiv": True,
            "url": "https://www.l-bank.de/"
        },
        "BE": {
            "name": "Berlin",
            "programm": "Stromspeicher-Programm",
            "aktiv": True,
            "url": "https://www.ibb.de/"
        },
        "HE": {
            "name": "Hessen",
            "programm": "WIBank Darlehen",
            "typ": "Zinszuschuss",
            "aktiv": True,
            "url": "https://www.wibank.de/"
        },
        "ST": {
            "name": "Sachsen-Anhalt",
            "programm": "Speicherförderung > 30 kWh",
            "bedingung_kwh_min": 30,
            "aktiv": True,
        },
        # Weitere Bundesländer - prüfen auf aktuelle Programme
        "BY": {"name": "Bayern", "aktiv": False, "hinweis": "Programm 2024 ausgelaufen"},
        "NW": {"name": "Nordrhein-Westfalen", "aktiv": False, "hinweis": "progres.nrw pausiert"},
        "NI": {"name": "Niedersachsen", "aktiv": False},
        "SH": {"name": "Schleswig-Holstein", "aktiv": False},
    }
}

# Marktstammdatenregister-Pflichten
MASTR_PFLICHTEN = {
    "frist_tage": 30,  # 1 Monat nach Inbetriebnahme
    "pflicht_pv": True,
    "pflicht_speicher": True,
    "sanktion": "Verlust der EEG-Vergütung",
    "url": "https://www.marktstammdatenregister.de",
    "benoetigte_daten": [
        "Installierte Leistung (kWp/kW)",
        "Speicherkapazität (kWh)",
        "Nutzbare Speicherkapazität (kWh)",
        "Netzbetreiber-ID",
        "Inbetriebnahmedatum",
        "Standortadresse",
        "EEG-Anlagetyp (Teileinspeisung/Volleinspeisung)",
    ]
}

# Technische Konstanten für Simulation
SIMULATION_DEFAULTS = {
    "pv_degradation_jahr": 0.005,     # 0.5% pro Jahr
    "battery_roundtrip_efficiency": 0.90,  # 90% (Laden + Entladen)
    "battery_soc_min": 0.10,          # 10% Minimum SOC
    "battery_soc_max": 0.90,          # 90% Maximum SOC
    "battery_calendar_life_years": 15,
    "battery_cycle_life": 6000,       # LFP typisch
    "pv_lifetime_years": 25,
    "project_lifetime_years": 20,     # Für NPV-Berechnung
    "discount_rate": 0.03,            # 3% für NPV
    "inflation_rate": 0.02,           # 2% Strompreissteigerung
    "co2_emission_factor": 0.363,     # kg CO2/kWh (Deutschland 2024, Quelle: Umweltbundesamt)
}


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
