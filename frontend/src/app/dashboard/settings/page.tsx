"use client";

import { useState, useEffect } from "react";
import {
  User,
  Building,
  Mail,
  Lock,
  Bell,
  Palette,
  Database,
  Key,
  Save,
  Loader2,
  CheckCircle,
  ExternalLink,
  RefreshCw,
  AlertCircle,
  Globe,
  FileSignature,
  MapPin,
  Sun,
} from "lucide-react";

interface IntegrationStatus {
  docusign: {
    configured: boolean;
    mode: string;
    features: string[];
  };
  hubspot: {
    configured: boolean;
    features: string[];
  };
  google_maps: {
    configured: boolean;
    features: string[];
  };
  pvgis: {
    configured: boolean;
    features: string[];
  };
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("profile");
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [integrationStatus, setIntegrationStatus] = useState<IntegrationStatus | null>(null);
  const [loadingIntegrations, setLoadingIntegrations] = useState(false);

  // Fetch integration status
  const fetchIntegrationStatus = async () => {
    setLoadingIntegrations(true);
    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/integrations/status`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      if (response.ok) {
        const data = await response.json();
        setIntegrationStatus(data);
      }
    } catch (error) {
      console.error("Failed to fetch integration status:", error);
    } finally {
      setLoadingIntegrations(false);
    }
  };

  useEffect(() => {
    if (activeTab === "integrations") {
      fetchIntegrationStatus();
    }
  }, [activeTab]);

  // Form states
  const [profile, setProfile] = useState({
    name: "Demo User",
    email: "demo@ews-gmbh.de",
    company: "EWS GmbH",
    phone: "+49 461 123456",
  });

  const [notifications, setNotifications] = useState({
    emailOffers: true,
    emailProjects: true,
    emailNewsletter: false,
  });

  const [defaults, setDefaults] = useState({
    defaultElectricityPrice: "0.30",
    defaultFeedInTariff: "0.082",
    defaultPvCost: "1000",
    defaultBatteryCost: "500",
    offerValidityDays: "30",
  });

  const handleSave = async () => {
    setIsSaving(true);
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setIsSaving(false);
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  const tabs = [
    { id: "profile", label: "Profil", icon: User },
    { id: "company", label: "Unternehmen", icon: Building },
    { id: "notifications", label: "Benachrichtigungen", icon: Bell },
    { id: "defaults", label: "Standardwerte", icon: Database },
    { id: "integrations", label: "Integrationen", icon: Key },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Einstellungen</h1>
        <p className="text-slate-500">
          Verwalten Sie Ihre Konto- und Anwendungseinstellungen
        </p>
      </div>

      <div className="grid lg:grid-cols-4 gap-6">
        {/* Sidebar Navigation */}
        <div className="lg:col-span-1">
          <nav className="card p-2 space-y-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left
                  transition-colors
                  ${
                    activeTab === tab.id
                      ? "bg-blue-50 text-blue-600"
                      : "text-slate-600 hover:bg-slate-50"
                  }
                `}
              >
                <tab.icon className="w-5 h-5" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="lg:col-span-3">
          <div className="card">
            {/* Profile Tab */}
            {activeTab === "profile" && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-semibold mb-1">Persönliche Daten</h2>
                  <p className="text-sm text-slate-500">
                    Aktualisieren Sie Ihre persönlichen Informationen
                  </p>
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="label">Name</label>
                    <input
                      type="text"
                      value={profile.name}
                      onChange={(e) =>
                        setProfile({ ...profile, name: e.target.value })
                      }
                      className="input-field"
                    />
                  </div>
                  <div>
                    <label className="label">E-Mail</label>
                    <input
                      type="email"
                      value={profile.email}
                      onChange={(e) =>
                        setProfile({ ...profile, email: e.target.value })
                      }
                      className="input-field"
                    />
                  </div>
                  <div>
                    <label className="label">Unternehmen</label>
                    <input
                      type="text"
                      value={profile.company}
                      onChange={(e) =>
                        setProfile({ ...profile, company: e.target.value })
                      }
                      className="input-field"
                    />
                  </div>
                  <div>
                    <label className="label">Telefon</label>
                    <input
                      type="tel"
                      value={profile.phone}
                      onChange={(e) =>
                        setProfile({ ...profile, phone: e.target.value })
                      }
                      className="input-field"
                    />
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-200">
                  <h3 className="font-medium mb-4">Passwort ändern</h3>
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <label className="label">Aktuelles Passwort</label>
                      <input
                        type="password"
                        placeholder="••••••••"
                        className="input-field"
                      />
                    </div>
                    <div>
                      <label className="label">Neues Passwort</label>
                      <input
                        type="password"
                        placeholder="••••••••"
                        className="input-field"
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Company Tab */}
            {activeTab === "company" && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-semibold mb-1">Unternehmensdaten</h2>
                  <p className="text-sm text-slate-500">
                    Diese Daten erscheinen auf Ihren Angeboten
                  </p>
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <div className="md:col-span-2">
                    <label className="label">Firmenname</label>
                    <input
                      type="text"
                      defaultValue="EWS GmbH"
                      className="input-field"
                    />
                  </div>
                  <div className="md:col-span-2">
                    <label className="label">Adresse</label>
                    <input
                      type="text"
                      defaultValue="Industriestraße 1, 24983 Handewitt"
                      className="input-field"
                    />
                  </div>
                  <div>
                    <label className="label">USt-IdNr.</label>
                    <input
                      type="text"
                      defaultValue="DE123456789"
                      className="input-field"
                    />
                  </div>
                  <div>
                    <label className="label">Handelsregister</label>
                    <input
                      type="text"
                      defaultValue="HRB 12345 FL"
                      className="input-field"
                    />
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-200">
                  <label className="label">Firmenlogo</label>
                  <div className="flex items-center gap-4">
                    <div className="w-20 h-20 bg-slate-100 rounded-lg flex items-center justify-center">
                      <Building className="w-10 h-10 text-slate-300" />
                    </div>
                    <button className="btn-secondary">Logo hochladen</button>
                  </div>
                </div>
              </div>
            )}

            {/* Notifications Tab */}
            {activeTab === "notifications" && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-semibold mb-1">Benachrichtigungen</h2>
                  <p className="text-sm text-slate-500">
                    Wählen Sie, worüber Sie informiert werden möchten
                  </p>
                </div>

                <div className="space-y-4">
                  <label className="flex items-center justify-between p-4 bg-slate-50 rounded-lg cursor-pointer">
                    <div>
                      <p className="font-medium">Angebots-Updates</p>
                      <p className="text-sm text-slate-500">
                        Benachrichtigungen wenn Angebote angesehen oder unterschrieben werden
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      checked={notifications.emailOffers}
                      onChange={(e) =>
                        setNotifications({
                          ...notifications,
                          emailOffers: e.target.checked,
                        })
                      }
                      className="w-5 h-5 rounded text-blue-600"
                    />
                  </label>

                  <label className="flex items-center justify-between p-4 bg-slate-50 rounded-lg cursor-pointer">
                    <div>
                      <p className="font-medium">Projekt-Updates</p>
                      <p className="text-sm text-slate-500">
                        Benachrichtigungen zu Projektänderungen
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      checked={notifications.emailProjects}
                      onChange={(e) =>
                        setNotifications({
                          ...notifications,
                          emailProjects: e.target.checked,
                        })
                      }
                      className="w-5 h-5 rounded text-blue-600"
                    />
                  </label>

                  <label className="flex items-center justify-between p-4 bg-slate-50 rounded-lg cursor-pointer">
                    <div>
                      <p className="font-medium">Newsletter</p>
                      <p className="text-sm text-slate-500">
                        Produktupdates und Branchennews
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      checked={notifications.emailNewsletter}
                      onChange={(e) =>
                        setNotifications({
                          ...notifications,
                          emailNewsletter: e.target.checked,
                        })
                      }
                      className="w-5 h-5 rounded text-blue-600"
                    />
                  </label>
                </div>
              </div>
            )}

            {/* Defaults Tab */}
            {activeTab === "defaults" && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-semibold mb-1">Standardwerte</h2>
                  <p className="text-sm text-slate-500">
                    Standardwerte für neue Projekte und Simulationen
                  </p>
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="label">Strompreis (€/kWh)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={defaults.defaultElectricityPrice}
                      onChange={(e) =>
                        setDefaults({
                          ...defaults,
                          defaultElectricityPrice: e.target.value,
                        })
                      }
                      className="input-field"
                    />
                  </div>
                  <div>
                    <label className="label">Einspeisevergütung (€/kWh)</label>
                    <input
                      type="number"
                      step="0.001"
                      value={defaults.defaultFeedInTariff}
                      onChange={(e) =>
                        setDefaults({
                          ...defaults,
                          defaultFeedInTariff: e.target.value,
                        })
                      }
                      className="input-field"
                    />
                  </div>
                  <div>
                    <label className="label">PV-Kosten (€/kWp)</label>
                    <input
                      type="number"
                      value={defaults.defaultPvCost}
                      onChange={(e) =>
                        setDefaults({
                          ...defaults,
                          defaultPvCost: e.target.value,
                        })
                      }
                      className="input-field"
                    />
                  </div>
                  <div>
                    <label className="label">Speicherkosten (€/kWh)</label>
                    <input
                      type="number"
                      value={defaults.defaultBatteryCost}
                      onChange={(e) =>
                        setDefaults({
                          ...defaults,
                          defaultBatteryCost: e.target.value,
                        })
                      }
                      className="input-field"
                    />
                  </div>
                  <div>
                    <label className="label">Angebots-Gültigkeit (Tage)</label>
                    <input
                      type="number"
                      value={defaults.offerValidityDays}
                      onChange={(e) =>
                        setDefaults({
                          ...defaults,
                          offerValidityDays: e.target.value,
                        })
                      }
                      className="input-field"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Integrations Tab */}
            {activeTab === "integrations" && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold mb-1">Integrationen</h2>
                    <p className="text-sm text-slate-500">
                      Verbinden Sie externe Dienste für erweiterte Funktionen
                    </p>
                  </div>
                  <button
                    onClick={fetchIntegrationStatus}
                    disabled={loadingIntegrations}
                    className="btn-secondary flex items-center gap-2"
                  >
                    <RefreshCw className={`w-4 h-4 ${loadingIntegrations ? "animate-spin" : ""}`} />
                    Aktualisieren
                  </button>
                </div>

                {loadingIntegrations && !integrationStatus ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* DocuSign */}
                    <div className={`flex items-center justify-between p-4 border rounded-lg ${
                      integrationStatus?.docusign?.configured
                        ? "border-emerald-200 bg-emerald-50"
                        : "border-slate-200"
                    }`}>
                      <div className="flex items-center gap-4">
                        <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                          integrationStatus?.docusign?.configured
                            ? "bg-emerald-100"
                            : "bg-blue-100"
                        }`}>
                          <FileSignature className={`w-6 h-6 ${
                            integrationStatus?.docusign?.configured
                              ? "text-emerald-600"
                              : "text-blue-600"
                          }`} />
                        </div>
                        <div>
                          <p className="font-medium">DocuSign E-Signatur</p>
                          {integrationStatus?.docusign?.configured ? (
                            <div className="flex items-center gap-2">
                              <CheckCircle className="w-4 h-4 text-emerald-600" />
                              <span className="text-sm text-emerald-700">
                                Verbunden ({integrationStatus.docusign.mode})
                              </span>
                            </div>
                          ) : (
                            <p className="text-sm text-slate-500">
                              Digitale Unterschriften für Angebote
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="text-right">
                        {integrationStatus?.docusign?.configured ? (
                          <div className="text-xs text-slate-500">
                            {integrationStatus.docusign.features.join(", ")}
                          </div>
                        ) : (
                          <button className="btn-secondary flex items-center gap-2">
                            Verbinden
                            <ExternalLink className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </div>

                    {/* HubSpot */}
                    <div className={`flex items-center justify-between p-4 border rounded-lg ${
                      integrationStatus?.hubspot?.configured
                        ? "border-emerald-200 bg-emerald-50"
                        : "border-slate-200"
                    }`}>
                      <div className="flex items-center gap-4">
                        <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                          integrationStatus?.hubspot?.configured
                            ? "bg-emerald-100"
                            : "bg-orange-100"
                        }`}>
                          <Globe className={`w-6 h-6 ${
                            integrationStatus?.hubspot?.configured
                              ? "text-emerald-600"
                              : "text-orange-600"
                          }`} />
                        </div>
                        <div>
                          <p className="font-medium">HubSpot CRM</p>
                          {integrationStatus?.hubspot?.configured ? (
                            <div className="flex items-center gap-2">
                              <CheckCircle className="w-4 h-4 text-emerald-600" />
                              <span className="text-sm text-emerald-700">Verbunden</span>
                            </div>
                          ) : (
                            <p className="text-sm text-slate-500">
                              Synchronisiere Kontakte, Firmen und Deals
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="text-right">
                        {integrationStatus?.hubspot?.configured ? (
                          <div className="text-xs text-slate-500">
                            {integrationStatus.hubspot.features.join(", ")}
                          </div>
                        ) : (
                          <button className="btn-secondary flex items-center gap-2">
                            Verbinden
                            <ExternalLink className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Google Maps */}
                    <div className={`flex items-center justify-between p-4 border rounded-lg ${
                      integrationStatus?.google_maps?.configured
                        ? "border-emerald-200 bg-emerald-50"
                        : "border-slate-200"
                    }`}>
                      <div className="flex items-center gap-4">
                        <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                          integrationStatus?.google_maps?.configured
                            ? "bg-emerald-100"
                            : "bg-red-100"
                        }`}>
                          <MapPin className={`w-6 h-6 ${
                            integrationStatus?.google_maps?.configured
                              ? "text-emerald-600"
                              : "text-red-600"
                          }`} />
                        </div>
                        <div>
                          <p className="font-medium">Google Maps API</p>
                          {integrationStatus?.google_maps?.configured ? (
                            <div className="flex items-center gap-2">
                              <CheckCircle className="w-4 h-4 text-emerald-600" />
                              <span className="text-sm text-emerald-700">Verbunden</span>
                            </div>
                          ) : (
                            <p className="text-sm text-slate-500">
                              Geocoding und Satellitenbilder
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="text-right">
                        {integrationStatus?.google_maps?.configured ? (
                          <div className="text-xs text-slate-500">
                            {integrationStatus.google_maps.features.join(", ")}
                          </div>
                        ) : (
                          <button className="btn-secondary flex items-center gap-2">
                            Konfigurieren
                            <ExternalLink className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </div>

                    {/* PVGIS */}
                    <div className="flex items-center justify-between p-4 border border-emerald-200 bg-emerald-50 rounded-lg">
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-emerald-100 rounded-lg flex items-center justify-center">
                          <Sun className="w-6 h-6 text-emerald-600" />
                        </div>
                        <div>
                          <p className="font-medium">PVGIS (EU JRC)</p>
                          <div className="flex items-center gap-2">
                            <CheckCircle className="w-4 h-4 text-emerald-600" />
                            <span className="text-sm text-emerald-700">
                              Immer verfügbar (Public API)
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="text-right text-xs text-slate-500">
                        {integrationStatus?.pvgis?.features?.join(", ") || "tmy-data, pv-estimation, monthly-radiation"}
                      </div>
                    </div>

                    {/* Info Box */}
                    <div className="flex items-start gap-3 p-4 bg-blue-50 border border-blue-200 rounded-lg mt-6">
                      <AlertCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                      <div className="text-sm text-blue-800">
                        <p className="font-medium mb-1">API-Schlüssel konfigurieren</p>
                        <p>
                          Integrationen werden über Umgebungsvariablen im Backend konfiguriert.
                          Kontaktieren Sie Ihren Administrator, um neue Integrationen zu aktivieren.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Save Button */}
            <div className="flex items-center justify-end gap-4 pt-6 mt-6 border-t border-slate-200">
              {saveSuccess && (
                <span className="flex items-center gap-2 text-emerald-600">
                  <CheckCircle className="w-5 h-5" />
                  Gespeichert
                </span>
              )}
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="btn-primary flex items-center gap-2"
              >
                {isSaving ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                Speichern
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
