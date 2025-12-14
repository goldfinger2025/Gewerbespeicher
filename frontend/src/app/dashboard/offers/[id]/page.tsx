"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  FileText,
  Download,
  Send,
  CheckCircle,
  Clock,
  ExternalLink,
  Loader2,
  Copy,
  Mail,
  Printer,
} from "lucide-react";
import api from "@/lib/api-client";

export default function OfferDetailPage() {
  const params = useParams();
  const router = useRouter();
  const offerId = params?.id as string;

  const [showSendModal, setShowSendModal] = useState(false);
  const [customerEmail, setCustomerEmail] = useState("");

  // Fetch offer
  const { data: offer, isLoading, error } = useQuery({
    queryKey: ["offer", offerId],
    queryFn: () => api.getOffer(offerId),
    enabled: !!offerId,
  });

  // Send offer mutation
  const sendOffer = useMutation({
    mutationFn: () => api.sendOffer(offerId, { customer_email: customerEmail }),
    onSuccess: () => {
      setShowSendModal(false);
      // Refetch offer to update status
    },
  });

  // Get signature link
  const getSignatureLink = useMutation({
    mutationFn: () => api.getSignatureLink(offerId),
    onSuccess: (data) => {
      window.open(data.signature_link, "_blank");
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error || !offer) {
    return (
      <div className="text-center py-12">
        <FileText className="w-16 h-16 text-slate-300 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-slate-900">
          Angebot nicht gefunden
        </h3>
        <Link href="/dashboard/offers" className="text-blue-600 mt-4 inline-block">
          Zurück zu Angeboten
        </Link>
      </div>
    );
  }

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/dashboard/offers"
            className="text-slate-400 hover:text-slate-600 transition"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-slate-900">
                {offer.offer_number}
              </h1>
              <span
                className={`px-3 py-1 rounded-full text-sm font-medium ${
                  statusColors[offer.status] || statusColors.draft
                }`}
              >
                {statusLabels[offer.status] || offer.status}
              </span>
            </div>
            <p className="text-slate-500">
              Erstellt am {new Date(offer.created_at).toLocaleDateString("de-DE")}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => window.print()}
            className="btn-secondary flex items-center gap-2"
          >
            <Printer className="w-4 h-4" />
            Drucken
          </button>
          {offer.status === "draft" && (
            <button
              onClick={() => setShowSendModal(true)}
              className="btn-primary flex items-center gap-2"
            >
              <Send className="w-4 h-4" />
              Senden
            </button>
          )}
        </div>
      </div>

      {/* Content Grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Offer Preview */}
          <div className="card">
            <div className="prose max-w-none">
              <div
                dangerouslySetInnerHTML={{
                  __html: offer.offer_text?.replace(/\n/g, "<br/>") || "",
                }}
              />
            </div>
          </div>

          {/* Validity Info */}
          <div className="card bg-amber-50 border-amber-200">
            <div className="flex items-center gap-3">
              <Clock className="w-5 h-5 text-amber-600" />
              <div>
                <p className="font-medium text-amber-900">
                  Angebot gültig bis:{" "}
                  {new Date(offer.valid_until).toLocaleDateString("de-DE")}
                </p>
                <p className="text-sm text-amber-700">
                  {Math.ceil(
                    (new Date(offer.valid_until).getTime() - Date.now()) /
                      (1000 * 60 * 60 * 24)
                  )}{" "}
                  Tage verbleibend
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="lg:col-span-1 space-y-6">
          {/* Actions */}
          <div className="card">
            <h3 className="font-semibold mb-4">Aktionen</h3>
            <div className="space-y-3">
              <button
                onClick={() => getSignatureLink.mutate()}
                disabled={getSignatureLink.isPending}
                className="w-full btn-secondary flex items-center justify-center gap-2"
              >
                {getSignatureLink.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <ExternalLink className="w-4 h-4" />
                )}
                E-Signatur Link
              </button>

              <button
                onClick={() => navigator.clipboard.writeText(window.location.href)}
                className="w-full btn-secondary flex items-center justify-center gap-2"
              >
                <Copy className="w-4 h-4" />
                Link kopieren
              </button>

              <button
                onClick={async () => {
                  try {
                    const blob = await api.getOfferPdf(offerId);
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `Angebot_${offer.offer_number}.pdf`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                  } catch (error) {
                    console.error('PDF download failed:', error);
                    alert('PDF konnte nicht heruntergeladen werden');
                  }
                }}
                className="w-full btn-secondary flex items-center justify-center gap-2"
              >
                <Download className="w-4 h-4" />
                PDF herunterladen
              </button>
            </div>
          </div>

          {/* Status History */}
          <div className="card">
            <h3 className="font-semibold mb-4">Status-Verlauf</h3>
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <div className="bg-emerald-100 p-1.5 rounded-full">
                  <CheckCircle className="w-4 h-4 text-emerald-600" />
                </div>
                <div>
                  <p className="font-medium text-sm">Angebot erstellt</p>
                  <p className="text-xs text-slate-500">
                    {new Date(offer.created_at).toLocaleString("de-DE")}
                  </p>
                </div>
              </div>

              {offer.status !== "draft" && (
                <div className="flex items-start gap-3">
                  <div className="bg-blue-100 p-1.5 rounded-full">
                    <Send className="w-4 h-4 text-blue-600" />
                  </div>
                  <div>
                    <p className="font-medium text-sm">Gesendet</p>
                    <p className="text-xs text-slate-500">
                      An Kunden gesendet
                    </p>
                  </div>
                </div>
              )}

              {offer.is_signed && (
                <div className="flex items-start gap-3">
                  <div className="bg-emerald-100 p-1.5 rounded-full">
                    <CheckCircle className="w-4 h-4 text-emerald-600" />
                  </div>
                  <div>
                    <p className="font-medium text-sm">Unterschrieben</p>
                    <p className="text-xs text-slate-500">
                      von {offer.signer_name || "Kunde"}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Related Project */}
          <div className="card">
            <h3 className="font-semibold mb-4">Verknüpftes Projekt</h3>
            <Link
              href={`/dashboard/planner/${offer.project_id}`}
              className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition"
            >
              <FileText className="w-5 h-5 text-slate-400" />
              <span className="text-sm font-medium">Projekt öffnen</span>
              <ArrowLeft className="w-4 h-4 ml-auto rotate-180" />
            </Link>
          </div>
        </div>
      </div>

      {/* Send Modal */}
      {showSendModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-bold mb-4">Angebot senden</h3>
            
            <div className="mb-4">
              <label className="label">E-Mail-Adresse des Kunden</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type="email"
                  value={customerEmail}
                  onChange={(e) => setCustomerEmail(e.target.value)}
                  className="input-field pl-10"
                  placeholder="kunde@firma.de"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowSendModal(false)}
                className="btn-secondary"
              >
                Abbrechen
              </button>
              <button
                onClick={() => sendOffer.mutate()}
                disabled={!customerEmail || sendOffer.isPending}
                className="btn-primary flex items-center gap-2"
              >
                {sendOffer.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
                Senden
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
