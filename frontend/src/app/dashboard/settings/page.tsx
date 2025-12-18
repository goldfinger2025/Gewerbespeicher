"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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
  Upload,
} from "lucide-react";
import { client } from "@/lib/api-client";

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

interface UserProfile {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  company_name?: string;
  phone?: string;
}

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("profile");
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [integrationStatus, setIntegrationStatus] = useState<IntegrationStatus | null>(null);
  const [loadingIntegrations, setLoadingIntegrations] = useState(false);

  // Password change state
  const [passwordData, setPasswordData] = useState({
    currentPassword: "",
    newPassword: "",
  });
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState(false);

  // Fetch current user profile
  const { data: userProfile, isLoading: profileLoading } = useQuery<UserProfile>({
    queryKey: ["user-profile"],
    queryFn: async () => {
      const response = await client.get("/auth/me");
      return response.data;
    },
  });

  // Update profile mutation
  const updateProfile = useMutation({
    mutationFn: async (data: { first_name?: string; last_name?: string; company_name?: string; phone?: string }) => {
      const response = await client.patch("/auth/me", null, { params: data });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user-profile"] });
      setSaveSuccess(true);
      setSaveError(null);
      setTimeout(() => setSaveSuccess(false), 3000);
    },
    onError: (error: any) => {
      setSaveError(error.response?.data?.detail || "Fehler beim Speichern");
    },
  });

  // Change password mutation
  const changePassword = useMutation({
    mutationFn: async (data: { current_password: string; new_password: string }) => {
      const response = await client.post("/auth/change-password", data);
      return response.data;
    },
    onSuccess: () => {
      setPasswordSuccess(true);
      setPasswordError(null);
      setPasswordData({ currentPassword: "", newPassword: "" });
      setTimeout(() => setPasswordSuccess(false), 3000);
    },
    onError: (error: any) => {
      setPasswordError(error.response?.data?.detail || "Fehler beim Ändern des Passworts");
    },
  });

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

  // Form states - initialized from user profile
  const [profile, setProfile] = useState({
    first_name: "",
    last_name: "",
    company_name: "",
    phone: "",
  });

  // Update profile state when user data loads
  useEffect(() => {
    if (userProfile) {
      setProfile({
        first_name: userProfile.first_name || "",
        last_name: userProfile.last_name || "",
        company_name: userProfile.company_name || "",
        phone: userProfile.phone || "",
      });
    }
  }, [userProfile]);

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

  const handleSaveProfile = async () => {
    updateProfile.mutate({
      first_name: profile.first_name || undefined,
      last_name: profile.last_name || undefined,
      company_name: profile.company_name || undefined,
      phone: profile.phone || undefined,
    });
  };

  const handleChangePassword = async () => {
    if (!passwordData.currentPassword || !passwordData.newPassword) {
      setPasswordError("Bitte beide Felder ausfüllen");
      return;
    }
    if (passwordData.newPassword.length < 8) {
      setPasswordError("Neues Passwort muss mindestens 8 Zeichen haben");
      return;
    }
    changePassword.mutate({
      current_password: passwordData.currentPassword,
      new_password: passwordData.newPassword,
    });
  };

  const handleSave = async () => {
    if (activeTab === "profile") {
      handleSaveProfile();
    } else {
      // For other tabs, show success (local storage for now)
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    }
  };

  const isSaving = updateProfile.isPending || changePassword.isPending;

  // Company Tab as a separate component for logo upload state management
  const CompanyTabContent = () => {
    const [companyLogo, setCompanyLogo] = useState<string | null>(() => {
      if (typeof window !== "undefined") {
        return localStorage.getItem("company_logo");
      }
      return null;
    });
    const [companyData, setCompanyData] = useState({
      name: "EWS GmbH",
      address: "Industriestraße 1, 24983 Handewitt",
      vatId: "DE123456789",
      registry: "HRB 12345 FL",
    });

    const handleLogoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        // Validate file type
        if (!file.type.startsWith("image/")) {
          alert("Bitte wählen Sie eine Bilddatei aus.");
          return;
        }
        // Validate file size (max 2MB)
        if (file.size > 2 * 1024 * 1024) {
          alert("Die Datei ist zu groß. Maximal 2MB erlaubt.");
          return;
        }

        const reader = new FileReader();
        reader.onloadend = () => {
          const base64 = reader.result as string;
          setCompanyLogo(base64);
          localStorage.setItem("company_logo", base64);
        };
        reader.readAsDataURL(file);
      }
    };

    const removeLogo = () => {
      setCompanyLogo(null);
      localStorage.removeItem("company_logo");
    };

    return (
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
              value={companyData.name}
              onChange={(e) => setCompanyData({ ...companyData, name: e.target.value })}
              className="input-field"
            />
          </div>
          <div className="md:col-span-2">
            <label className="label">Adresse</label>
            <input
              type="text"
              value={companyData.address}
              onChange={(e) => setCompanyData({ ...companyData, address: e.target.value })}
              className="input-field"
            />
          </div>
          <div>
            <label className="label">USt-IdNr.</label>
            <input
              type="text"
              value={companyData.vatId}
              onChange={(e) => setCompanyData({ ...companyData, vatId: e.target.value })}
              className="input-field"
            />
          </div>
          <div>
            <label className="label">Handelsregister</label>
            <input
              type="text"
              value={companyData.registry}
              onChange={(e) => setCompanyData({ ...companyData, registry: e.target.value })}
              className="input-field"
            />
          </div>
        </div>

        <div className="pt-4 border-t border-slate-200">
          <label className="label">Firmenlogo</label>
          <div className="flex items-center gap-4">
            <div className="w-20 h-20 bg-slate-100 rounded-lg flex items-center justify-center overflow-hidden">
              {companyLogo ? (
                <img src={companyLogo} alt="Firmenlogo" className="w-full h-full object-contain" />
              ) : (
                <Building className="w-10 h-10 text-slate-300" />
              )}
            </div>
            <div className="flex flex-col gap-2">
              <label className="btn-secondary cursor-pointer inline-flex items-center gap-2">
                <Upload className="w-4 h-4" />
                Logo hochladen
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleLogoUpload}
                  className="hidden"
                />
              </label>
              {companyLogo && (
                <button
                  onClick={removeLogo}
                  className="text-sm text-red-600 hover:text-red-700"
                >
                  Logo entfernen
                </button>
              )}
              <p className="text-xs text-slate-400">PNG, JPG oder SVG (max. 2MB)</p>
            </div>
          </div>
        </div>
      </div>
    );
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

                {profileLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                  </div>
                ) : (
                  <>
                    {saveError && (
                      <div className="bg-red-50 text-red-600 px-4 py-3 rounded-lg text-sm">
                        {saveError}
                      </div>
                    )}

                    <div className="grid md:grid-cols-2 gap-4">
                      <div>
                        <label className="label">Vorname</label>
                        <input
                          type="text"
                          value={profile.first_name}
                          onChange={(e) =>
                            setProfile({ ...profile, first_name: e.target.value })
                          }
                          className="input-field"
                          placeholder="Max"
                        />
                      </div>
                      <div>
                        <label className="label">Nachname</label>
                        <input
                          type="text"
                          value={profile.last_name}
                          onChange={(e) =>
                            setProfile({ ...profile, last_name: e.target.value })
                          }
                          className="input-field"
                          placeholder="Mustermann"
                        />
                      </div>
                      <div>
                        <label className="label">E-Mail</label>
                        <input
                          type="email"
                          value={userProfile?.email || ""}
                          disabled
                          className="input-field bg-slate-50 text-slate-500 cursor-not-allowed"
                        />
                        <p className="text-xs text-slate-400 mt-1">E-Mail kann nicht geändert werden</p>
                      </div>
                      <div>
                        <label className="label">Unternehmen</label>
                        <input
                          type="text"
                          value={profile.company_name}
                          onChange={(e) =>
                            setProfile({ ...profile, company_name: e.target.value })
                          }
                          className="input-field"
                          placeholder="Firma GmbH"
                        />
                      </div>
                      <div className="md:col-span-2">
                        <label className="label">Telefon</label>
                        <input
                          type="tel"
                          value={profile.phone}
                          onChange={(e) =>
                            setProfile({ ...profile, phone: e.target.value })
                          }
                          className="input-field"
                          placeholder="+49 123 456789"
                        />
                      </div>
                    </div>
                  </>
                )}

                <div className="pt-4 border-t border-slate-200">
                  <h3 className="font-medium mb-4">Passwort ändern</h3>

                  {passwordError && (
                    <div className="bg-red-50 text-red-600 px-4 py-3 rounded-lg text-sm mb-4">
                      {passwordError}
                    </div>
                  )}

                  {passwordSuccess && (
                    <div className="bg-emerald-50 text-emerald-600 px-4 py-3 rounded-lg text-sm mb-4 flex items-center gap-2">
                      <CheckCircle className="w-4 h-4" />
                      Passwort erfolgreich geändert
                    </div>
                  )}

                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <label className="label">Aktuelles Passwort</label>
                      <input
                        type="password"
                        placeholder="••••••••"
                        value={passwordData.currentPassword}
                        onChange={(e) => setPasswordData({ ...passwordData, currentPassword: e.target.value })}
                        className="input-field"
                      />
                    </div>
                    <div>
                      <label className="label">Neues Passwort</label>
                      <input
                        type="password"
                        placeholder="Mindestens 8 Zeichen"
                        value={passwordData.newPassword}
                        onChange={(e) => setPasswordData({ ...passwordData, newPassword: e.target.value })}
                        className="input-field"
                      />
                    </div>
                  </div>
                  <button
                    onClick={handleChangePassword}
                    disabled={changePassword.isPending}
                    className="btn-secondary mt-4 flex items-center gap-2"
                  >
                    {changePassword.isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Lock className="w-4 h-4" />
                    )}
                    Passwort ändern
                  </button>
                </div>
              </div>
            )}

            {/* Company Tab */}
            {activeTab === "company" && (
              <CompanyTabContent />
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
