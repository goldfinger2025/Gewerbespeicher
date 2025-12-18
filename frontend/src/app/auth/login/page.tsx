"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Battery, Mail, Lock, Loader2, ArrowRight } from "lucide-react";
import api from "@/lib/api-client";

const loginSchema = z.object({
  email: z.string().email("Ungültige E-Mail-Adresse"),
  password: z.string().min(6, "Passwort muss mindestens 6 Zeichen haben"),
});

type LoginFormData = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  const onSubmit = async (data: LoginFormData) => {
    setIsLoading(true);
    setError(null);

    try {
      await api.login(data.email, data.password);
      router.push("/dashboard");
    } catch (err: any) {
      setError(
        err.response?.data?.detail || 
        "Anmeldung fehlgeschlagen. Bitte überprüfen Sie Ihre Zugangsdaten."
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
            Willkommen zurück
          </h1>
          <p className="text-slate-400">
            Melden Sie sich an, um Ihre Projekte zu verwalten
          </p>
        </div>

        {/* Login Form */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
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

            {/* Password Field */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="label mb-0">Passwort</label>
                <Link
                  href="/auth/forgot-password"
                  className="text-sm text-blue-600 hover:text-blue-700"
                >
                  Passwort vergessen?
                </Link>
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  {...register("password")}
                  type="password"
                  className="input-field pl-10"
                  placeholder="••••••••"
                  autoComplete="current-password"
                />
              </div>
              {errors.password && (
                <p className="text-red-500 text-sm mt-1">{errors.password.message}</p>
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
                  Wird angemeldet...
                </>
              ) : (
                <>
                  Anmelden
                  <ArrowRight className="w-5 h-5" />
                </>
              )}
            </button>
          </form>

          {/* Demo Account Notice - only shown in development */}
          {process.env.NODE_ENV === "development" && (
            <div className="mt-6 pt-6 border-t border-slate-200">
              <p className="text-center text-sm text-slate-500 mb-3">
                Demo-Zugang (nur Entwicklung):
              </p>
              <div className="bg-slate-50 rounded-lg p-3 text-sm text-slate-600">
                <p><strong>E-Mail:</strong> demo@ews-gmbh.de</p>
                <p><strong>Passwort:</strong> Demo1234</p>
              </div>
            </div>
          )}

          {/* Register Link */}
          <p className="text-center text-sm text-slate-600 mt-6">
            Noch kein Konto?{" "}
            <Link
              href="/auth/register"
              className="text-blue-600 hover:text-blue-700 font-medium"
            >
              Jetzt registrieren
            </Link>
          </p>
        </div>

        {/* Footer */}
        <p className="text-center text-sm text-slate-500 mt-8">
          © 2025 EWS GmbH • Gewerbespeicher Planner
        </p>
      </div>
    </div>
  );
}
