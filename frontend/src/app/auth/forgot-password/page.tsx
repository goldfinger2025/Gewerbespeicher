"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Battery, Mail, Loader2, ArrowLeft, CheckCircle } from "lucide-react";
import { client } from "@/lib/api-client";

const forgotPasswordSchema = z.object({
  email: z.string().email("Ungültige E-Mail-Adresse"),
});

type ForgotPasswordFormData = z.infer<typeof forgotPasswordSchema>;

export default function ForgotPasswordPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordFormData>({
    resolver: zodResolver(forgotPasswordSchema),
  });

  const onSubmit = async (data: ForgotPasswordFormData) => {
    setIsLoading(true);
    setError(null);

    try {
      await client.post("/auth/forgot-password", { email: data.email });
      setIsSubmitted(true);
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
        "Ein Fehler ist aufgetreten. Bitte versuchen Sie es erneut."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo & Title */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2 mb-4">
            <Battery className="w-10 h-10 text-emerald-400" />
            <span className="text-2xl font-bold text-white">
              Gewerbespeicher
            </span>
          </Link>
          <h1 className="text-3xl font-bold text-white mb-2">
            Passwort vergessen
          </h1>
          <p className="text-slate-400">
            Geben Sie Ihre E-Mail-Adresse ein, um Ihr Passwort zurückzusetzen
          </p>
        </div>

        {/* Form Card */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          {isSubmitted ? (
            <div className="text-center py-4">
              <div className="bg-emerald-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="w-8 h-8 text-emerald-600" />
              </div>
              <h2 className="text-xl font-semibold text-slate-900 mb-2">
                E-Mail gesendet
              </h2>
              <p className="text-slate-500 mb-6">
                Falls ein Konto mit dieser E-Mail existiert, haben wir Ihnen
                einen Link zum Zurücksetzen des Passworts gesendet.
              </p>
              <p className="text-sm text-slate-400 mb-6">
                Bitte überprüfen Sie auch Ihren Spam-Ordner.
              </p>
              <Link
                href="/auth/login"
                className="btn-primary inline-flex items-center gap-2"
              >
                <ArrowLeft className="w-4 h-4" />
                Zurück zur Anmeldung
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
              {/* Error Message */}
              {error && (
                <div className="bg-red-50 text-red-600 px-4 py-3 rounded-lg text-sm">
                  {error}
                </div>
              )}

              {/* Email Field */}
              <div>
                <label className="label">E-Mail-Adresse</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input
                    {...register("email")}
                    type="email"
                    className="input-field pl-10"
                    placeholder="ihre@email.de"
                    autoComplete="email"
                  />
                </div>
                {errors.email && (
                  <p className="text-red-500 text-sm mt-1">{errors.email.message}</p>
                )}
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="btn-primary w-full py-3 flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Wird gesendet...
                  </>
                ) : (
                  "Link zum Zurücksetzen senden"
                )}
              </button>
            </form>
          )}

          {/* Back to Login Link */}
          {!isSubmitted && (
            <p className="text-center text-sm text-slate-600 mt-6">
              <Link
                href="/auth/login"
                className="text-blue-600 hover:text-blue-700 font-medium inline-flex items-center gap-1"
              >
                <ArrowLeft className="w-4 h-4" />
                Zurück zur Anmeldung
              </Link>
            </p>
          )}
        </div>

        {/* Footer */}
        <p className="text-center text-sm text-slate-500 mt-8">
          &copy; 2025 EWS GmbH &bull; Gewerbespeicher Planner
        </p>
      </div>
    </div>
  );
}
