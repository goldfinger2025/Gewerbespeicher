"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  FileText,
  Plus,
  Clock,
  CheckCircle,
  Send,
  Eye,
  ArrowRight,
  Loader2,
  RefreshCw,
} from "lucide-react";
import api from "@/lib/api-client";

interface Offer {
  id: string;
  offer_number: string;
  status: string;
  created_at: string;
  valid_until: string;
  is_signed: boolean;
  project_id: string;
}

export default function OffersPage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["offers"],
    queryFn: async () => {
      const response = await api.getOffers();
      return response;
    },
  });

  const offers: Offer[] = data?.items || [];
  const total = data?.total || 0;

  const statusColors: Record<string, string> = {
    draft: "bg-slate-100 text-slate-700",
    sent: "bg-blue-100 text-blue-700",
    viewed: "bg-amber-100 text-amber-700",
    signed: "bg-emerald-100 text-emerald-700",
    completed: "bg-green-100 text-green-700",
    rejected: "bg-red-100 text-red-700",
  };

  const statusLabels: Record<string, string> = {
    draft: "Entwurf",
    sent: "Gesendet",
    viewed: "Angesehen",
    signed: "Unterschrieben",
    completed: "Abgeschlossen",
    rejected: "Abgelehnt",
  };

  const statusIcons: Record<string, typeof Clock> = {
    draft: FileText,
    sent: Send,
    viewed: Eye,
    signed: CheckCircle,
    completed: CheckCircle,
    rejected: FileText,
  };

  // Calculate stats
  const draftCount = offers.filter((o) => o.status === "draft").length;
  const sentCount = offers.filter((o) => o.status === "sent" || o.status === "viewed").length;
  const completedCount = offers.filter((o) => o.status === "completed" || o.status === "signed").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Angebote</h1>
          <p className="text-slate-500">
            Verwalten Sie Ihre Angebote und verfolgen Sie den Status
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => refetch()}
            className="btn-secondary flex items-center gap-2"
            disabled={isLoading}
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            Aktualisieren
          </button>
          <Link href="/dashboard/planner" className="btn-primary flex items-center gap-2">
            <Plus className="w-5 h-5" />
            Neues Projekt
          </Link>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card">
          <p className="text-sm text-slate-500">Gesamt</p>
          <p className="text-2xl font-bold">{total}</p>
        </div>
        <div className="card">
          <p className="text-sm text-slate-500">Entwürfe</p>
          <p className="text-2xl font-bold">{draftCount}</p>
        </div>
        <div className="card">
          <p className="text-sm text-slate-500">Gesendet</p>
          <p className="text-2xl font-bold">{sentCount}</p>
        </div>
        <div className="card">
          <p className="text-sm text-slate-500">Abgeschlossen</p>
          <p className="text-2xl font-bold">{completedCount}</p>
        </div>
      </div>

      {/* Offers List */}
      <div className="card">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
            <span className="ml-3 text-slate-500">Lade Angebote...</span>
          </div>
        ) : error ? (
          <div className="text-center py-12">
            <FileText className="w-16 h-16 text-red-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-slate-900 mb-2">
              Fehler beim Laden
            </h3>
            <p className="text-slate-500 mb-6">
              Die Angebote konnten nicht geladen werden.
            </p>
            <button
              onClick={() => refetch()}
              className="btn-primary inline-flex items-center gap-2"
            >
              <RefreshCw className="w-5 h-5" />
              Erneut versuchen
            </button>
          </div>
        ) : offers.length > 0 ? (
          <div className="divide-y divide-slate-200">
            {offers.map((offer: Offer) => {
              const StatusIcon = statusIcons[offer.status] || FileText;
              const isExpired = offer.valid_until && new Date(offer.valid_until) < new Date();

              return (
                <div
                  key={offer.id}
                  className="flex items-center justify-between py-4 first:pt-0 last:pb-0 hover:bg-slate-50 -mx-6 px-6 transition"
                >
                  <div className="flex items-center gap-4">
                    <div
                      className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                        statusColors[offer.status]?.split(" ")[0] || "bg-slate-100"
                      }`}
                    >
                      <StatusIcon className={`w-5 h-5 ${
                        statusColors[offer.status]?.split(" ")[1] || "text-slate-700"
                      }`} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-900">
                        {offer.offer_number}
                      </h3>
                      <p className="text-sm text-slate-500">
                        Erstellt am{" "}
                        {new Date(offer.created_at).toLocaleDateString("de-DE")}
                        {offer.valid_until && (
                          <span className={isExpired ? "text-red-500 ml-2" : "ml-2"}>
                            • Gültig bis {new Date(offer.valid_until).toLocaleDateString("de-DE")}
                            {isExpired && " (Abgelaufen)"}
                          </span>
                        )}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span
                      className={`px-3 py-1 rounded-full text-sm font-medium ${
                        statusColors[offer.status] || statusColors.draft
                      }`}
                    >
                      {statusLabels[offer.status] || offer.status}
                    </span>
                    <Link
                      href={`/dashboard/offers/${offer.id}`}
                      className="text-blue-600 hover:text-blue-700 p-2 hover:bg-blue-50 rounded-lg transition"
                    >
                      <ArrowRight className="w-5 h-5" />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-12">
            <FileText className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-slate-900 mb-2">
              Noch keine Angebote
            </h3>
            <p className="text-slate-500 mb-6 max-w-md mx-auto">
              Erstellen Sie ein Projekt, führen Sie eine Simulation durch und
              generieren Sie dann ein Angebot.
            </p>
            <Link href="/dashboard/planner" className="btn-primary inline-flex items-center gap-2">
              <Plus className="w-5 h-5" />
              Projekt erstellen
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
