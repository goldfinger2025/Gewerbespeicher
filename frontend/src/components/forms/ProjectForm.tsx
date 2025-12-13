"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2 } from "lucide-react";

// Validation Schema
const projectFormSchema = z.object({
  customer_name: z.string().min(2, "Name muss mindestens 2 Zeichen haben"),
  customer_email: z.string().email("Ungültige E-Mail").optional().or(z.literal("")),
  address: z.string().min(5, "Adresse erforderlich"),
  postal_code: z.string().regex(/^\d{5}$/, "Ungültige PLZ (5 Ziffern)"),
  city: z.string().optional(),
  project_name: z.string().optional(),
  pv_peak_power_kw: z.coerce
    .number()
    .min(1, "Min. 1 kWp")
    .max(1000, "Max. 1000 kWp"),
  battery_capacity_kwh: z.coerce
    .number()
    .min(5, "Min. 5 kWh")
    .max(2000, "Max. 2000 kWh"),
  battery_power_kw: z.coerce.number().min(1).max(500).optional(),
  annual_consumption_kwh: z.coerce
    .number()
    .min(1000, "Min. 1.000 kWh")
    .max(10000000, "Max. 10.000.000 kWh"),
  electricity_price_eur_kwh: z.coerce
    .number()
    .min(0.05)
    .max(1.0)
    .optional()
    .default(0.30),
});

type ProjectFormData = z.infer<typeof projectFormSchema>;

interface ProjectFormProps {
  onSubmit: (data: ProjectFormData) => Promise<void>;
  initialData?: Partial<ProjectFormData>;
  isEditing?: boolean;
}

export function ProjectForm({ onSubmit, initialData, isEditing = false }: ProjectFormProps) {
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ProjectFormData>({
    resolver: zodResolver(projectFormSchema),
    defaultValues: {
      customer_name: "",
      customer_email: "",
      address: "",
      postal_code: "",
      city: "",
      project_name: "",
      pv_peak_power_kw: 50,
      battery_capacity_kwh: 100,
      battery_power_kw: 50,
      annual_consumption_kwh: 50000,
      electricity_price_eur_kwh: 0.30,
      ...initialData,
    },
  });

  const handleFormSubmit = async (data: ProjectFormData) => {
    setIsLoading(true);
    try {
      await onSubmit(data);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
      {/* Kundenname */}
      <div>
        <label className="label">Kundenname *</label>
        <input
          {...register("customer_name")}
          className="input-field"
          placeholder="Max Mustermann GmbH"
        />
        {errors.customer_name && (
          <p className="text-red-500 text-sm mt-1">{errors.customer_name.message}</p>
        )}
      </div>

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

      {/* PLZ + Stadt */}
      <div className="grid grid-cols-2 gap-4">
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
        <div>
          <label className="label">Stadt</label>
          <input
            {...register("city")}
            className="input-field"
            placeholder="Handewitt"
          />
        </div>
      </div>

      {/* Divider */}
      <hr className="my-4 border-slate-200" />

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
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isLoading}
        className="btn-primary w-full flex items-center justify-center gap-2"
      >
        {isLoading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Wird gespeichert...
          </>
        ) : isEditing ? (
          "Projekt aktualisieren"
        ) : (
          "Projekt erstellen"
        )}
      </button>
    </form>
  );
}
