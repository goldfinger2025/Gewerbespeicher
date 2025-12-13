"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Battery, Loader2 } from "lucide-react";
import api from "@/lib/api-client";
import { ProjectForm } from "@/components/forms/ProjectForm";

export default function NewProjectPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  const createProject = useMutation({
    mutationFn: (data: any) => api.createProject(data),
    onSuccess: (result) => {
      router.push(`/dashboard/planner/${result.id}`);
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || "Fehler beim Erstellen des Projekts");
    },
  });

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <Link
          href="/dashboard"
          className="text-slate-400 hover:text-slate-600 transition"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Neues Projekt</h1>
          <p className="text-slate-500">
            Erfassen Sie die Projektdaten für die PV-Speicher-Simulation
          </p>
        </div>
      </div>

      {/* Form Card */}
      <div className="card">
        <div className="flex items-center gap-3 mb-6 pb-6 border-b border-slate-200">
          <div className="bg-blue-100 p-3 rounded-lg">
            <Battery className="w-6 h-6 text-blue-600" />
          </div>
          <div>
            <h2 className="font-semibold text-lg">Projektkonfiguration</h2>
            <p className="text-sm text-slate-500">
              Alle Felder mit * sind erforderlich
            </p>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 text-red-600 px-4 py-3 rounded-lg text-sm mb-6">
            {error}
          </div>
        )}

        <ProjectForm
          onSubmit={async (data) => {
            setError(null);
            await createProject.mutateAsync(data);
          }}
        />
      </div>

      {/* Help Text */}
      <div className="mt-6 text-center text-sm text-slate-500">
        Nach dem Erstellen können Sie eine Simulation starten und ein 
        Angebot generieren lassen.
      </div>
    </div>
  );
}
