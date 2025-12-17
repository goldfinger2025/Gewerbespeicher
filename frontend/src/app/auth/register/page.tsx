"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Battery, Mail, Lock, User, Building, Loader2, ArrowRight } from "lucide-react";
import api from "@/lib/api-client";

const registerSchema = z.object({
  first_name: z.string().min(2, "Vorname muss mindestens 2 Zeichen haben"),
  last_name: z.string().min(2, "Nachname muss mindestens 2 Zeichen haben"),
  email: z.string().email("Ungültige E-Mail-Adresse"),
  company_name: z.string().optional(),
  password: z.string().min(8, "Passwort muss mindestens 8 Zeichen haben"),
  password_confirm: z.string(),
}).refine((data) => data.password === data.password_confirm, {
  message: "Passwörter stimmen nicht überein",
  path: ["password_confirm"],
});

type RegisterFormData = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const router = useRouter();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      first_name: "",
      last_name: "",
      email: "",
      company_name: "",
      password: "",
      password_confirm: "",
    },
  });

  const onSubmit = async (data: RegisterFormData) => {
    setIsLoading(true);
    setError(null);

    try {
      await api.register({
        email: data.email,
        password: data.password,
        first_name: data.first_name,
        last_name: data.last_name,
        company_name: data.company_name,
      });
      setSuccess(true);
      // Redirect to login after 2 seconds
      setTimeout(() => {
        router.push("/auth/login");
      }, 2000);
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
        "Registrierung fehlgeschlagen. Bitte versuchen Sie es erneut."
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
            Konto erstellen
          </h1>
          <p className="text-slate-400">
            Registrieren Sie sich, um PV-Speicher-Projekte zu planen
          </p>
        </div>

        {/* Register Form */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          {success ? (
            <div className="text-center py-8">
              <div className="bg-emerald-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                <ArrowRight className="w-8 h-8 text-emerald-600" />
              </div>
              <h2 className="text-xl font-semibold text-slate-900 mb-2">
                Registrierung erfolgreich!
              </h2>
              <p className="text-slate-500">
                Sie werden zur Anmeldung weitergeleitet...
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              {/* Error Message */}
              {error && (
                <div className="bg-red-50 text-red-600 px-4 py-3 rounded-lg text-sm">
                  {error}
                </div>
              )}

              {/* Name Fields */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label">Vorname *</label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                    <input
                      {...register("first_name")}
                      type="text"
                      className="input-field pl-10"
                      placeholder="Max"
                    />
                  </div>
                  {errors.first_name && (
                    <p className="text-red-500 text-sm mt-1">{errors.first_name.message}</p>
                  )}
                </div>
                <div>
                  <label className="label">Nachname *</label>
                  <input
                    {...register("last_name")}
                    type="text"
                    className="input-field"
                    placeholder="Mustermann"
                  />
                  {errors.last_name && (
                    <p className="text-red-500 text-sm mt-1">{errors.last_name.message}</p>
                  )}
                </div>
              </div>

              {/* Email Field */}
              <div>
                <label className="label">E-Mail-Adresse *</label>
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

              {/* Company Name Field */}
              <div>
                <label className="label">Firmenname (optional)</label>
                <div className="relative">
                  <Building className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input
                    {...register("company_name")}
                    type="text"
                    className="input-field pl-10"
                    placeholder="Firma GmbH"
                  />
                </div>
              </div>

              {/* Password Field */}
              <div>
                <label className="label">Passwort *</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input
                    {...register("password")}
                    type="password"
                    className="input-field pl-10"
                    placeholder="Mindestens 8 Zeichen"
                    autoComplete="new-password"
                  />
                </div>
                {errors.password && (
                  <p className="text-red-500 text-sm mt-1">{errors.password.message}</p>
                )}
              </div>

              {/* Confirm Password Field */}
              <div>
                <label className="label">Passwort bestätigen *</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input
                    {...register("password_confirm")}
                    type="password"
                    className="input-field pl-10"
                    placeholder="Passwort wiederholen"
                    autoComplete="new-password"
                  />
                </div>
                {errors.password_confirm && (
                  <p className="text-red-500 text-sm mt-1">{errors.password_confirm.message}</p>
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
                    Wird registriert...
                  </>
                ) : (
                  <>
                    Konto erstellen
                    <ArrowRight className="w-5 h-5" />
                  </>
                )}
              </button>
            </form>
          )}

          {/* Login Link */}
          {!success && (
            <p className="text-center text-sm text-slate-600 mt-6">
              Bereits ein Konto?{" "}
              <Link
                href="/auth/login"
                className="text-blue-600 hover:text-blue-700 font-medium"
              >
                Jetzt anmelden
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
