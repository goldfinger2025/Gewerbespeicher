"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2, Building2, User, MapPin, Zap, Battery, Sun, Euro, ChevronDown, ChevronUp } from "lucide-react";

// Load Profile Types for Commercial Buildings
const LOAD_PROFILE_TYPES = [
  { value: "office", label: "Bürogebäude", description: "Mo-Fr 8-18 Uhr Hauptlast" },
  { value: "retail", label: "Einzelhandel", description: "Mo-Sa 10-20 Uhr Hauptlast" },
  { value: "production", label: "Produktion", description: "Schichtbetrieb, konstante Last" },
  { value: "warehouse", label: "Lager/Logistik", description: "Frühe Morgenstunden Hauptlast" },
] as const;

// German Bundesländer for regional info
const BUNDESLAENDER = [
  { value: "", label: "-- Bitte wählen --" },
  { value: "BW", label: "Baden-Württemberg" },
  { value: "BY", label: "Bayern" },
  { value: "BE", label: "Berlin" },
  { value: "BB", label: "Brandenburg" },
  { value: "HB", label: "Bremen" },
  { value: "HH", label: "Hamburg" },
  { value: "HE", label: "Hessen" },
  { value: "MV", label: "Mecklenburg-Vorpommern" },
  { value: "NI", label: "Niedersachsen" },
  { value: "NW", label: "Nordrhein-Westfalen" },
  { value: "RP", label: "Rheinland-Pfalz" },
  { value: "SL", label: "Saarland" },
  { value: "SN", label: "Sachsen" },
  { value: "ST", label: "Sachsen-Anhalt" },
  { value: "SH", label: "Schleswig-Holstein" },
  { value: "TH", label: "Thüringen" },
] as const;

// Validation Schema
const projectFormSchema = z.object({
  // Customer Information
  customer_name: z.string().min(2, "Name muss mindestens 2 Zeichen haben"),
  customer_company: z.string().optional(),
  customer_email: z.string().email("Ungültige E-Mail").optional().or(z.literal("")),
  customer_phone: z.string().optional(),

  // Location
  address: z.string().min(5, "Adresse erforderlich"),
  postal_code: z.string().regex(/^\d{5}$/, "Ungültige PLZ (5 Ziffern)"),
  city: z.string().optional(),
  bundesland: z.string().optional(),

  // Project
  project_name: z.string().optional(),
  description: z.string().optional(),
  load_profile_type: z.enum(["office", "retail", "production", "warehouse"]).default("office"),

  // PV System
  pv_peak_power_kw: z.coerce
    .number()
    .min(1, "Min. 1 kWp")
    .max(1000, "Max. 1000 kWp"),
  pv_tilt_angle: z.coerce.number().min(0).max(90).optional().default(30),
  roof_area_sqm: z.coerce.number().min(0).optional(),

  // Battery System
  battery_capacity_kwh: z.coerce
    .number()
    .min(5, "Min. 5 kWh")
    .max(2000, "Max. 2000 kWh"),
  battery_power_kw: z.coerce.number().min(1).max(500).optional(),

  // Consumption
  annual_consumption_kwh: z.coerce
    .number()
    .min(1000, "Min. 1.000 kWh")
    .max(10000000, "Max. 10.000.000 kWh"),
  peak_load_kw: z.coerce.number().min(0).optional(),

  // Costs
  electricity_price_eur_kwh: z.coerce
    .number()
    .min(0.05)
    .max(1.0)
    .optional()
    .default(0.30),
  feed_in_tariff_eur_kwh: z.coerce
    .number()
    .min(0)
    .max(0.20)
    .optional()
    .default(0.08),
});

type ProjectFormData = z.infer<typeof projectFormSchema>;

interface ProjectFormProps {
  onSubmit: (data: ProjectFormData) => Promise<void>;
  initialData?: Partial<ProjectFormData>;
  isEditing?: boolean;
}

export function ProjectForm({ onSubmit, initialData, isEditing = false }: ProjectFormProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<ProjectFormData>({
    resolver: zodResolver(projectFormSchema),
    defaultValues: {
      // Customer
      customer_name: "",
      customer_company: "",
      customer_email: "",
      customer_phone: "",
      // Location
      address: "",
      postal_code: "",
      city: "",
      bundesland: "",
      // Project
      project_name: "",
      description: "",
      load_profile_type: "office",
      // PV System
      pv_peak_power_kw: 50,
      pv_tilt_angle: 30,
      roof_area_sqm: undefined,
      // Battery
      battery_capacity_kwh: 100,
      battery_power_kw: 50,
      // Consumption
      annual_consumption_kwh: 50000,
      peak_load_kw: undefined,
      // Costs
      electricity_price_eur_kwh: 0.30,
      feed_in_tariff_eur_kwh: 0.08,
      ...initialData,
    },
  });

  const pvPower = watch("pv_peak_power_kw");
  const batteryCapacity = watch("battery_capacity_kwh");

  const handleFormSubmit = async (data: ProjectFormData) => {
    setIsLoading(true);
    try {
      await onSubmit(data);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
      {/* Section: Kundeninformationen */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-slate-700 font-medium">
          <User className="w-4 h-4" />
          <span>Kundeninformationen</span>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          {/* Kundenname */}
          <div>
            <label className="label">Ansprechpartner *</label>
            <input
              {...register("customer_name")}
              className="input-field"
              placeholder="Max Mustermann"
            />
            {errors.customer_name && (
              <p className="text-red-500 text-sm mt-1">{errors.customer_name.message}</p>
            )}
          </div>

          {/* Firma */}
          <div>
            <label className="label">Unternehmen</label>
            <input
              {...register("customer_company")}
              className="input-field"
              placeholder="Mustermann GmbH"
            />
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          {/* Email */}
          <div>
            <label className="label">E-Mail</label>
            <input
              {...register("customer_email")}
              type="email"
              className="input-field"
              placeholder="kunde@firma.de"
            />
            {errors.customer_email && (
              <p className="text-red-500 text-sm mt-1">{errors.customer_email.message}</p>
            )}
          </div>

          {/* Telefon */}
          <div>
            <label className="label">Telefon</label>
            <input
              {...register("customer_phone")}
              type="tel"
              className="input-field"
              placeholder="+49 123 456789"
            />
          </div>
        </div>
      </div>

      {/* Section: Standort */}
      <div className="space-y-4 pt-4 border-t border-slate-200">
        <div className="flex items-center gap-2 text-slate-700 font-medium">
          <MapPin className="w-4 h-4" />
          <span>Standort</span>
        </div>

        {/* Projektname */}
        <div>
          <label className="label">Projektname</label>
          <input
            {...register("project_name")}
            className="input-field"
            placeholder="z.B. PV-Anlage Logistikzentrum Nord"
          />
        </div>

        {/* Adresse */}
        <div>
          <label className="label">Adresse *</label>
          <input
            {...register("address")}
            className="input-field"
            placeholder="Musterstraße 123"
          />
          {errors.address && (
            <p className="text-red-500 text-sm mt-1">{errors.address.message}</p>
          )}
        </div>

        {/* PLZ + Stadt + Bundesland */}
        <div className="grid grid-cols-4 gap-4">
          <div>
            <label className="label">PLZ *</label>
            <input
              {...register("postal_code")}
              className="input-field"
              placeholder="24983"
              maxLength={5}
            />
            {errors.postal_code && (
              <p className="text-red-500 text-sm mt-1">{errors.postal_code.message}</p>
            )}
          </div>
          <div className="col-span-2">
            <label className="label">Stadt</label>
            <input
              {...register("city")}
              className="input-field"
              placeholder="Handewitt"
            />
          </div>
          <div>
            <label className="label">Bundesland</label>
            <select {...register("bundesland")} className="input-field">
              {BUNDESLAENDER.map((bl) => (
                <option key={bl.value} value={bl.value}>{bl.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Section: Gebäude & Verbrauch */}
      <div className="space-y-4 pt-4 border-t border-slate-200">
        <div className="flex items-center gap-2 text-slate-700 font-medium">
          <Building2 className="w-4 h-4" />
          <span>Gebäude & Verbrauch</span>
        </div>

        {/* Lastprofil-Typ */}
        <div>
          <label className="label">Gebäudetyp / Lastprofil *</label>
          <select
            {...register("load_profile_type")}
            className="input-field"
          >
            {LOAD_PROFILE_TYPES.map((profile) => (
              <option key={profile.value} value={profile.value}>
                {profile.label} – {profile.description}
              </option>
            ))}
          </select>
          <p className="text-slate-500 text-xs mt-1">
            Das Lastprofil beeinflusst die Berechnung des Eigenverbrauchs
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          {/* Jahresverbrauch */}
          <div>
            <label className="label">Jahresverbrauch (kWh) *</label>
            <input
              {...register("annual_consumption_kwh")}
              type="number"
              step="100"
              className="input-field"
              placeholder="50000"
            />
            {errors.annual_consumption_kwh && (
              <p className="text-red-500 text-sm mt-1">{errors.annual_consumption_kwh.message}</p>
            )}
          </div>

          {/* Spitzenlast */}
          <div>
            <label className="label">Spitzenlast (kW)</label>
            <input
              {...register("peak_load_kw")}
              type="number"
              step="1"
              className="input-field"
              placeholder="z.B. 80"
            />
            <p className="text-slate-500 text-xs mt-1">
              Für Peak-Shaving-Analyse
            </p>
          </div>
        </div>
      </div>

      {/* Section: Systemkonfiguration */}
      <div className="space-y-4 pt-4 border-t border-slate-200">
        <div className="flex items-center gap-2 text-slate-700 font-medium">
          <Sun className="w-4 h-4" />
          <span>PV-Anlage</span>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          {/* PV-Leistung */}
          <div>
            <label className="label">PV-Leistung (kWp) *</label>
            <input
              {...register("pv_peak_power_kw")}
              type="number"
              step="0.1"
              className="input-field"
              placeholder="50"
            />
            {errors.pv_peak_power_kw && (
              <p className="text-red-500 text-sm mt-1">{errors.pv_peak_power_kw.message}</p>
            )}
          </div>

          {/* Dachfläche */}
          <div>
            <label className="label">Dachfläche (m²)</label>
            <input
              {...register("roof_area_sqm")}
              type="number"
              step="1"
              className="input-field"
              placeholder="z.B. 400"
            />
            <p className="text-slate-500 text-xs mt-1">
              Ca. 6 m² pro kWp benötigt
            </p>
          </div>
        </div>
      </div>

      {/* Section: Speicher */}
      <div className="space-y-4 pt-4 border-t border-slate-200">
        <div className="flex items-center gap-2 text-slate-700 font-medium">
          <Battery className="w-4 h-4" />
          <span>Batteriespeicher</span>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          {/* Speicherkapazität */}
          <div>
            <label className="label">Speicherkapazität (kWh) *</label>
            <input
              {...register("battery_capacity_kwh")}
              type="number"
              step="1"
              className="input-field"
              placeholder="100"
            />
            {errors.battery_capacity_kwh && (
              <p className="text-red-500 text-sm mt-1">{errors.battery_capacity_kwh.message}</p>
            )}
          </div>

          {/* Speicherleistung */}
          <div>
            <label className="label">Speicherleistung (kW)</label>
            <input
              {...register("battery_power_kw")}
              type="number"
              step="1"
              className="input-field"
              placeholder={String(Math.round((batteryCapacity || 100) * 0.5))}
            />
            <p className="text-slate-500 text-xs mt-1">
              Standard: 0,5 × Kapazität
            </p>
          </div>
        </div>

        {/* Quick Info */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <p className="text-sm text-blue-800">
            <strong>Systemübersicht:</strong> {pvPower || 50} kWp PV + {batteryCapacity || 100} kWh Speicher
            <br />
            <span className="text-blue-600">
              Verhältnis: 1:{((batteryCapacity || 100) / (pvPower || 50)).toFixed(1)} (kWh:kWp) –
              {(batteryCapacity || 100) / (pvPower || 50) < 1.5 ? " ROI-optimiert" :
               (batteryCapacity || 100) / (pvPower || 50) > 2.5 ? " Autarkie-optimiert" : " ausgewogen"}
            </span>
          </p>
        </div>
      </div>

      {/* Section: Wirtschaftlichkeit (Advanced) */}
      <div className="pt-4 border-t border-slate-200">
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-2 text-slate-600 hover:text-slate-800 transition"
        >
          <Euro className="w-4 h-4" />
          <span className="font-medium">Wirtschaftliche Parameter</span>
          {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {showAdvanced && (
          <div className="mt-4 space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              {/* Strompreis */}
              <div>
                <label className="label">Strompreis (€/kWh)</label>
                <input
                  {...register("electricity_price_eur_kwh")}
                  type="number"
                  step="0.01"
                  className="input-field"
                  placeholder="0.30"
                />
                <p className="text-slate-500 text-xs mt-1">
                  Aktueller Arbeitspreis inkl. aller Abgaben
                </p>
              </div>

              {/* Einspeisevergütung */}
              <div>
                <label className="label">Einspeisevergütung (€/kWh)</label>
                <input
                  {...register("feed_in_tariff_eur_kwh")}
                  type="number"
                  step="0.001"
                  className="input-field"
                  placeholder="0.08"
                />
                <p className="text-slate-500 text-xs mt-1">
                  EEG-Vergütung für Überschusseinspeisung
                </p>
              </div>
            </div>

            {/* Dachneigung */}
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="label">Dachneigung (°)</label>
                <input
                  {...register("pv_tilt_angle")}
                  type="number"
                  step="1"
                  className="input-field"
                  placeholder="30"
                />
                <p className="text-slate-500 text-xs mt-1">
                  Optimal: 30-35° in Deutschland
                </p>
              </div>
            </div>

            {/* Beschreibung */}
            <div>
              <label className="label">Projektnotizen</label>
              <textarea
                {...register("description")}
                className="input-field min-h-[80px]"
                placeholder="Zusätzliche Informationen zum Projekt..."
              />
            </div>
          </div>
        )}
      </div>

      {/* Submit Button */}
      <div className="pt-4">
        <button
          type="submit"
          disabled={isLoading}
          className="btn-primary w-full flex items-center justify-center gap-2 py-3"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Wird gespeichert...
            </>
          ) : isEditing ? (
            "Projekt aktualisieren"
          ) : (
            "Projekt erstellen"
          )}
        </button>
      </div>
    </form>
  );
}
