"""
Compliance-Service für Gewerbespeicher-Installateure
=====================================================

Generiert projektspezifische Checklisten für gesetzliche Anforderungen,
Anmeldepflichten und wichtige Fristen.

Ziel: Installateure sollen alle rechtlichen Pflichten auf einen Blick
haben und keine kritischen Fristen verpassen.

Stand: Dezember 2025
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

from app.config import (
    PARA_14A_ENWG,
    MASTR_PFLICHTEN,
    EEG_FEED_IN_TARIFFS,
    FOERDERUNGEN,
    NETZENTGELT_SCHWELLEN
)

logger = logging.getLogger(__name__)


@dataclass
class ChecklistItem:
    """Ein Punkt auf der Compliance-Checkliste"""
    task: str
    beschreibung: str
    frist: Optional[str]
    pflicht: bool
    kategorie: str
    url: Optional[str] = None
    wichtig: Optional[str] = None
    erledigt: bool = False


class ComplianceService:
    """
    Service zur Generierung von Compliance-Checklisten für Installateure

    Berücksichtigt:
    - Marktstammdatenregister (MaStR)
    - §14a EnWG (Steuerbare Verbrauchseinrichtungen)
    - EEG-Anforderungen
    - Netzanschlussbedingungen
    - Fördervoraussetzungen
    """

    def __init__(self):
        self.mastr = MASTR_PFLICHTEN
        self.para_14a = PARA_14A_ENWG
        self.eeg = EEG_FEED_IN_TARIFFS
        self.foerderungen = FOERDERUNGEN

    def generate_project_checklist(
        self,
        pv_kwp: float,
        battery_kwh: float,
        battery_power_kw: float,
        jahresverbrauch_kwh: float,
        bundesland: str = None,
        inbetriebnahme_datum: datetime = None,
        eeg_typ: str = "teileinspeisung"
    ) -> Dict:
        """
        Generiert projektspezifische Compliance-Checkliste

        Args:
            pv_kwp: PV-Leistung in kWp
            battery_kwh: Speicherkapazität in kWh
            battery_power_kw: Speicherleistung in kW
            jahresverbrauch_kwh: Erwarteter Jahresverbrauch
            bundesland: Bundesland-Kürzel (z.B. "BY", "NW")
            inbetriebnahme_datum: Geplantes/tatsächliches Datum
            eeg_typ: "teileinspeisung" oder "volleinspeisung"

        Returns:
            Dict mit kategorisierten Checklisten
        """
        if inbetriebnahme_datum is None:
            inbetriebnahme_datum = datetime.now()

        checklist = {
            "vor_installation": [],
            "bei_installation": [],
            "nach_installation": [],
            "laufend": [],
            "fristen": [],
            "warnungen": []
        }

        # ================================================================
        # VOR INSTALLATION
        # ================================================================

        # Netzanschlussanmeldung
        checklist["vor_installation"].append({
            "task": "Netzanschlussanmeldung beim Netzbetreiber",
            "beschreibung": "Anmeldung der PV-Anlage und des Speichers beim zuständigen Verteilnetzbetreiber",
            "pflicht": True,
            "frist": "Vor Installationsbeginn",
            "hinweis": "Ohne Genehmigung keine Installation! Bearbeitungszeit ca. 4-8 Wochen einplanen.",
            "dokumente": [
                "Antragsformular des Netzbetreibers",
                "Lageplan des Grundstücks",
                "Technische Datenblätter (Module, Wechselrichter, Speicher)",
                "Einheitenzertifikat nach VDE-AR-N 4105",
            ]
        })

        # Förderung VOR Bestellung!
        if self._has_applicable_subsidy(pv_kwp, battery_kwh, bundesland):
            checklist["vor_installation"].append({
                "task": "Förderantrag stellen",
                "beschreibung": "WICHTIG: Förderung muss VOR Bestellung/Auftragsvergabe beantragt werden!",
                "pflicht": False,
                "frist": "VOR jeglicher Bestellung",
                "wichtig": "Nach Bestellung/Vertragsschluss ist Förderung oft ausgeschlossen!",
                "programme": self._get_applicable_subsidies(pv_kwp, battery_kwh, bundesland)
            })

        # Direktvermarktung prüfen
        if pv_kwp > 25:
            checklist["vor_installation"].append({
                "task": "Direktvermarktung prüfen",
                "beschreibung": f"Ab 25 kWp ist Direktvermarktung zu prüfen (ab 100 kWp Pflicht)",
                "pflicht": pv_kwp > 100,
                "frist": "Vor Inbetriebnahme",
                "hinweis": "Direktvermarktungsvertrag mit Aggregator/Direktvermarkter abschließen",
                "aktueller_status": "Pflicht ab 100 kWp, Absenkung auf 25 kWp geplant bis 2027"
            })

        # ================================================================
        # BEI INSTALLATION
        # ================================================================

        # §14a EnWG - Steuerbare Verbrauchseinrichtung
        if battery_power_kw > self.para_14a["schwelle_kw"]:
            checklist["bei_installation"].append({
                "task": "§14a EnWG - Steuerbare Verbrauchseinrichtung",
                "beschreibung": f"Speicher > {self.para_14a['schwelle_kw']} kW muss netzdienlich steuerbar sein",
                "pflicht": True,
                "frist": "Bei Installation",
                "technisch": "Steuerbox/Smart-Meter-Gateway für Netzbetreiber-Zugriff",
                "vorteil": "Ermöglicht Netzentgelt-Reduktion (Modul 1 oder 2)",
                "module": [
                    {
                        "name": self.para_14a["module"]["modul1"]["name"],
                        "beschreibung": self.para_14a["module"]["modul1"]["beschreibung"],
                        "ersparnis": f"{self.para_14a['module']['modul1']['erstattung_min']}-{self.para_14a['module']['modul1']['erstattung_max']} €/Jahr"
                    },
                    {
                        "name": self.para_14a["module"]["modul2"]["name"],
                        "beschreibung": self.para_14a["module"]["modul2"]["beschreibung"],
                        "ersparnis": "60% Rabatt auf Netzentgelt",
                        "voraussetzung": self.para_14a["module"]["modul2"]["voraussetzung"]
                    }
                ]
            })

        # Zählerwesen
        checklist["bei_installation"].append({
            "task": "Zählerkonzept mit Netzbetreiber abstimmen",
            "beschreibung": "Klärung der Zähleranordnung (Zweirichtungszähler, Speicherzähler, etc.)",
            "pflicht": True,
            "frist": "Vor/Bei Installation",
            "optionen": [
                "Zweirichtungszähler (Standard für PV)",
                "Separater Speicherzähler (für §14a Modul 2)",
                "Smart Meter / iMSys (für zeitvariable Tarife)"
            ]
        })

        # RLM-Messung für Großverbraucher
        if jahresverbrauch_kwh >= NETZENTGELT_SCHWELLEN["rlm_messung_ab_kwh"]:
            checklist["bei_installation"].append({
                "task": "Registrierende Leistungsmessung (RLM) prüfen",
                "beschreibung": f"Ab {NETZENTGELT_SCHWELLEN['rlm_messung_ab_kwh']:,} kWh/Jahr ist 15-Min-Leistungsmessung üblich",
                "pflicht": True,
                "hinweis": "Leistungspreis wird auf Basis der höchsten Lastspitze berechnet - Peak-Shaving sinnvoll!",
                "peak_shaving_empfehlung": True
            })

        # ================================================================
        # NACH INSTALLATION
        # ================================================================

        # MaStR-Registrierung - KRITISCH!
        mastr_frist = inbetriebnahme_datum + timedelta(days=self.mastr["frist_tage"])
        checklist["nach_installation"].append({
            "task": "Marktstammdatenregister (MaStR) - PV-Anlage",
            "beschreibung": "Registrierung der PV-Anlage im Marktstammdatenregister",
            "pflicht": True,
            "frist": mastr_frist.strftime("%d.%m.%Y"),
            "frist_tage": self.mastr["frist_tage"],
            "url": self.mastr["url"],
            "wichtig": self.mastr["sanktion"],
            "benoetigte_daten": [
                "Installierte Leistung (kWp)",
                "Inbetriebnahmedatum",
                "Standortadresse",
                "Netzbetreiber",
                "EEG-Anlagetyp",
                "Wechselrichter-Daten"
            ]
        })

        checklist["nach_installation"].append({
            "task": "Marktstammdatenregister (MaStR) - Speicher",
            "beschreibung": "Registrierung des Batteriespeichers im Marktstammdatenregister",
            "pflicht": True,
            "frist": mastr_frist.strftime("%d.%m.%Y"),
            "frist_tage": self.mastr["frist_tage"],
            "url": self.mastr["url"],
            "wichtig": "Speicher SEPARAT zur PV-Anlage anmelden!",
            "benoetigte_daten": [
                "Speicherkapazität (kWh)",
                "Nutzbare Speicherkapazität (kWh)",
                "Speicherleistung (kW)",
                "Technologie (z.B. Lithium-Eisenphosphat)",
                "AC- oder DC-gekoppelt"
            ]
        })

        # ZEREZ-Registrierung (NEU ab 02/2025)
        checklist["nach_installation"].append({
            "task": "ZEREZ-Registrierung",
            "beschreibung": "Zentralregister für Einheiten- und Komponentenzertifikate",
            "pflicht": True,
            "frist": "Bei Inbetriebnahme",
            "neu_seit": "Februar 2025",
            "hinweis": "Neue Pflicht für alle PV-Anlagen ab Februar 2025"
        })

        # Inbetriebnahmeprotokoll
        checklist["nach_installation"].append({
            "task": "Inbetriebnahmeprotokoll erstellen",
            "beschreibung": "Dokumentation der Inbetriebnahme mit allen relevanten Messwerten",
            "pflicht": True,
            "frist": "Bei Inbetriebnahme",
            "inhalt": [
                "Anlagenleistung und Konfiguration",
                "Isolationsmessung",
                "Erdungsmessung",
                "Wechselrichter-Parametrierung",
                "Speicher-Einstellungen (SOC-Grenzen, etc.)",
                "Netzeinspeisung-Test"
            ]
        })

        # ================================================================
        # LAUFENDE PFLICHTEN
        # ================================================================

        checklist["laufend"].append({
            "task": "MaStR-Datenpflege",
            "beschreibung": "Änderungen (Leistungsänderung, Stilllegung, etc.) innerhalb 1 Monat melden",
            "pflicht": True,
            "rhythmus": "Bei Änderungen",
            "url": self.mastr["url"]
        })

        checklist["laufend"].append({
            "task": "EEG-Meldepflichten",
            "beschreibung": "Jährliche Meldung der eingespeisten Strommengen an Netzbetreiber",
            "pflicht": True,
            "rhythmus": "Jährlich (meist bis 28.02.)",
        })

        if pv_kwp > 100:
            checklist["laufend"].append({
                "task": "Direktvermarktung - Abrechnungen",
                "beschreibung": "Monatliche Abrechnung mit Direktvermarkter",
                "pflicht": True,
                "rhythmus": "Monatlich"
            })

        # ================================================================
        # FRISTEN ÜBERSICHT
        # ================================================================

        checklist["fristen"].append({
            "was": "MaStR-Registrierung",
            "frist": mastr_frist.strftime("%d.%m.%Y"),
            "kritisch": True,
            "konsequenz": "Verlust EEG-Vergütung"
        })

        # ================================================================
        # WARNUNGEN
        # ================================================================

        # EEG 2025: Negative Strompreise
        checklist["warnungen"].append({
            "titel": "Solarspitzengesetz 2025",
            "beschreibung": "Bei negativen Strompreisen an der Börse wird KEINE EEG-Vergütung gezahlt",
            "gilt_ab": "25.02.2025 (für Neuanlagen)",
            "ausgleich": "Zeit ohne Vergütung wird an Ende der 20 Jahre angehängt",
            "empfehlung": "Eigenverbrauchsoptimierung durch Speicher reduziert dieses Risiko"
        })

        # EEG-Degression
        checklist["warnungen"].append({
            "titel": "EEG-Degression",
            "beschreibung": f"Einspeisevergütung sinkt halbjährlich um {self.eeg['degression_prozent']*100:.0f}%",
            "naechste_absenkung": self.eeg["naechste_degression"],
            "empfehlung": "Frühere Inbetriebnahme sichert höhere Vergütung für 20 Jahre"
        })

        return {
            "projekt": {
                "pv_kwp": pv_kwp,
                "battery_kwh": battery_kwh,
                "battery_power_kw": battery_power_kw,
                "jahresverbrauch_kwh": jahresverbrauch_kwh,
                "bundesland": bundesland,
                "inbetriebnahme": inbetriebnahme_datum.strftime("%d.%m.%Y"),
            },
            "checkliste": checklist,
            "zusammenfassung": self._generate_summary(checklist),
            "stand": datetime.now().strftime("%d.%m.%Y")
        }

    def get_eeg_vergütung(
        self,
        pv_kwp: float,
        eeg_typ: str = "teileinspeisung"
    ) -> Dict:
        """
        Berechnet die aktuelle EEG-Vergütung für eine Anlagengröße

        Args:
            pv_kwp: PV-Leistung in kWp
            eeg_typ: "teileinspeisung" oder "volleinspeisung"

        Returns:
            Dict mit Vergütungsdetails
        """
        tarife = self.eeg.get(eeg_typ, self.eeg["teileinspeisung"])

        # Gestaffelte Vergütung berechnen
        if pv_kwp <= 10:
            rate = tarife["bis_10kwp"]
            stufe = "bis 10 kWp"
        elif pv_kwp <= 40:
            # Anteilig berechnen
            rate_10 = tarife["bis_10kwp"]
            rate_40 = tarife["10_40kwp"]
            # Gewichteter Durchschnitt
            anteil_10 = 10 / pv_kwp
            anteil_40 = (pv_kwp - 10) / pv_kwp
            rate = rate_10 * anteil_10 + rate_40 * anteil_40
            stufe = "10-40 kWp (anteilig)"
        elif pv_kwp <= 100:
            rate_10 = tarife["bis_10kwp"]
            rate_40 = tarife["10_40kwp"]
            rate_100 = tarife.get("40_100kwp", tarife["10_40kwp"])
            anteil_10 = 10 / pv_kwp
            anteil_40 = 30 / pv_kwp
            anteil_100 = (pv_kwp - 40) / pv_kwp
            rate = rate_10 * anteil_10 + rate_40 * anteil_40 + rate_100 * anteil_100
            stufe = "40-100 kWp (anteilig)"
        else:
            rate = tarife.get("ueber_100kwp", 0.068)
            stufe = "über 100 kWp"

        return {
            "verguetung_eur_kwh": round(rate, 4),
            "verguetung_ct_kwh": round(rate * 100, 2),
            "stufe": stufe,
            "typ": eeg_typ,
            "stand": self.eeg["stand"],
            "gueltig_bis": self.eeg["gueltig_bis"],
            "hinweis_degression": f"Nächste Absenkung: {self.eeg['naechste_degression']} (-{self.eeg['degression_prozent']*100:.0f}%)",
            "direktvermarktung_pflicht": pv_kwp > 100,
            "direktvermarktung_empfohlen": pv_kwp > 25
        }

    def get_para_14a_info(
        self,
        battery_power_kw: float
    ) -> Dict:
        """
        Prüft §14a EnWG Relevanz und gibt Informationen

        Args:
            battery_power_kw: Speicherleistung in kW

        Returns:
            Dict mit §14a-Informationen
        """
        betroffen = battery_power_kw > self.para_14a["schwelle_kw"]

        if not betroffen:
            return {
                "betroffen": False,
                "grund": f"Speicherleistung ({battery_power_kw} kW) unter Schwelle ({self.para_14a['schwelle_kw']} kW)",
                "handlung_erforderlich": False
            }

        return {
            "betroffen": True,
            "speicherleistung_kw": battery_power_kw,
            "schwelle_kw": self.para_14a["schwelle_kw"],
            "pflichten": [
                "Speicher muss netzdienlich steuerbar sein",
                "Anmeldung als steuerbare Verbrauchseinrichtung",
                "Steuerbox oder Smart-Meter-Gateway erforderlich"
            ],
            "vorteile": {
                "modul1": {
                    "name": self.para_14a["module"]["modul1"]["name"],
                    "ersparnis": f"{self.para_14a['module']['modul1']['erstattung_default']} €/Jahr (ca.)",
                    "voraussetzung": "Standard, keine zusätzliche Hardware"
                },
                "modul2": {
                    "name": self.para_14a["module"]["modul2"]["name"],
                    "ersparnis": "60% Netzentgelt-Rabatt",
                    "voraussetzung": "Separater Zähler erforderlich"
                },
                "modul3": {
                    "name": self.para_14a["module"]["modul3"]["name"],
                    "verfuegbar_ab": self.para_14a["module"]["modul3"]["verfuegbar_ab"],
                    "voraussetzung": "Smart Meter (iMSys)"
                }
            },
            "empfehlung": "Modul 2 oft wirtschaftlich attraktiver bei hohem Verbrauch über Speicher",
            "uebergangsfrist_bestand": self.para_14a["uebergangsfrist_bestand"]
        }

    def _has_applicable_subsidy(
        self,
        pv_kwp: float,
        battery_kwh: float,
        bundesland: str
    ) -> bool:
        """Prüft ob Förderungen verfügbar sind"""
        # Bundesförderung immer verfügbar
        if pv_kwp <= 30:  # MwSt-Befreiung
            return True

        # KfW 270 immer verfügbar
        return True

    def _get_applicable_subsidies(
        self,
        pv_kwp: float,
        battery_kwh: float,
        bundesland: str
    ) -> List[Dict]:
        """Gibt Liste anwendbarer Förderungen zurück"""
        subsidies = []

        # Bundesförderungen
        for key, foerderung in self.foerderungen["bund"].items():
            if foerderung.get("aktiv", False):
                applicable = True

                # Prüfe Bedingungen
                if "bedingung_kwp_max" in foerderung:
                    applicable = pv_kwp <= foerderung["bedingung_kwp_max"]

                if applicable:
                    subsidies.append({
                        "name": foerderung["name"],
                        "typ": foerderung["typ"],
                        "url": foerderung.get("url"),
                        "ebene": "Bund",
                        "wichtig": foerderung.get("antragstellung")
                    })

        # Landesförderungen
        if bundesland and bundesland in self.foerderungen["laender"]:
            land = self.foerderungen["laender"][bundesland]
            if land.get("aktiv", False):
                applicable = True

                if "bedingung_kwh_min" in land:
                    applicable = battery_kwh >= land["bedingung_kwh_min"]

                if applicable:
                    subsidies.append({
                        "name": f"{land['name']} - {land['programm']}",
                        "typ": land.get("typ", "Förderung"),
                        "url": land.get("url"),
                        "ebene": "Land",
                    })

        return subsidies

    def _generate_summary(self, checklist: Dict) -> Dict:
        """Generiert Zusammenfassung der Checkliste"""
        total_tasks = 0
        pflicht_tasks = 0
        kritische_fristen = []

        for kategorie, items in checklist.items():
            if kategorie in ["fristen", "warnungen"]:
                continue

            for item in items:
                total_tasks += 1
                if item.get("pflicht", False):
                    pflicht_tasks += 1

        for frist in checklist.get("fristen", []):
            if frist.get("kritisch", False):
                kritische_fristen.append(f"{frist['was']}: {frist['frist']}")

        return {
            "gesamt_aufgaben": total_tasks,
            "pflichtaufgaben": pflicht_tasks,
            "kritische_fristen": kritische_fristen,
            "warnungen_anzahl": len(checklist.get("warnungen", []))
        }


# Singleton
_compliance_service: Optional[ComplianceService] = None


def get_compliance_service() -> ComplianceService:
    """Gibt Compliance-Service-Instanz zurück"""
    global _compliance_service
    if _compliance_service is None:
        _compliance_service = ComplianceService()
    return _compliance_service
