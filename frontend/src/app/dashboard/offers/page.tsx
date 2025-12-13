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
} from "lucide-react";

export default function OffersPage() {
  // For now, show empty state - offers are created from simulations
  const offers: any[] = [];

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
        <Link href="/dashboard/planner" className="btn-primary flex items-center gap-2">
          <Plus className="w-5 h-5" />
          Neues Projekt
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card">
          <p className="text-sm text-slate-500">Gesamt</p>
          <p className="text-2xl font-bold">{offers.length}</p>
        </div>
        <div className="card">
          <p className="text-sm text-slate-500">Entwürfe</p>
          <p className="text-2xl font-bold">
            {offers.filter((o) => o.status === "draft").length}
          </p>
        </div>
        <div className="card">
          <p className="text-sm text-slate-500">Gesendet</p>
          <p className="text-2xl font-bold">
            {offers.filter((o) => o.status === "sent").length}
          </p>
        </div>
        <div className="card">
          <p className="text-sm text-slate-500">Abgeschlossen</p>
          <p className="text-2xl font-bold">
            {offers.filter((o) => o.status === "completed" || o.status === "signed").length}
          </p>
        </div>
      </div>

      {/* Offers List */}
      <div className="card">
        {offers.length > 0 ? (
          <div className="divide-y divide-slate-200">
            {offers.map((offer: any) => {
              const StatusIcon = statusIcons[offer.status] || FileText;
              return (
                <div
                  key={offer.id}
                  className="flex items-center justify-between py-4 first:pt-0 last:pb-0"
                >
                  <div className="flex items-center gap-4">
                    <div
                      className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                        statusColors[offer.status]?.split(" ")[0] || "bg-slate-100"
                      }`}
                    >
                      <StatusIcon className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-900">
                        {offer.offer_number}
                      </h3>
                      <p className="text-sm text-slate-500">
                        Erstellt am{" "}
                        {new Date(offer.created_at).toLocaleDateString("de-DE")}
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
                      className="text-blue-600 hover:text-blue-700"
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
