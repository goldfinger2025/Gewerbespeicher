"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Battery,
  LayoutDashboard,
  FolderOpen,
  Calculator,
  FileText,
  Settings,
  LogOut,
  Menu,
  X,
  ChevronRight,
  User,
  Loader2,
} from "lucide-react";
import api, { client } from "@/lib/api-client";

interface UserInfo {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  company_name?: string;
}

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Projekte", href: "/dashboard/projects", icon: FolderOpen },
  { name: "Neues Projekt", href: "/dashboard/planner", icon: Calculator },
  { name: "Angebote", href: "/dashboard/offers", icon: FileText },
  { name: "Einstellungen", href: "/dashboard/settings", icon: Settings },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [user, setUser] = useState<UserInfo | null>(null);
  const [userLoading, setUserLoading] = useState(true);

  // Fetch current user info on mount
  useEffect(() => {
    const fetchUser = async () => {
      try {
        const response = await client.get("/auth/me");
        setUser(response.data);
      } catch (error) {
        // If unauthorized, redirect to login
        router.push("/auth/login");
      } finally {
        setUserLoading(false);
      }
    };
    fetchUser();
  }, [router]);

  const handleLogout = () => {
    api.logout();
    router.push("/auth/login");
  };

  // Helper to get display name
  const displayName = user?.first_name && user?.last_name
    ? `${user.first_name} ${user.last_name}`
    : user?.email?.split("@")[0] || "Benutzer";

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed top-0 left-0 z-50 h-full w-64 bg-slate-900 text-white
          transform transition-transform duration-200 ease-in-out
          lg:translate-x-0
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
        `}
      >
        {/* Logo */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <Link href="/dashboard" className="flex items-center gap-2">
            <Battery className="w-8 h-8 text-emerald-400" />
            <span className="font-bold text-lg">Gewerbespeicher</span>
          </Link>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden text-slate-400 hover:text-white"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.name}
                href={item.href}
                onClick={() => setSidebarOpen(false)}
                className={`
                  flex items-center gap-3 px-4 py-3 rounded-lg
                  transition-colors duration-150
                  ${
                    isActive
                      ? "bg-emerald-600 text-white"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }
                `}
              >
                <item.icon className="w-5 h-5" />
                {item.name}
                {isActive && <ChevronRight className="w-4 h-4 ml-auto" />}
              </Link>
            );
          })}
        </nav>

        {/* User Section */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-slate-700">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-slate-700 rounded-full flex items-center justify-center">
              {userLoading ? (
                <Loader2 className="w-5 h-5 text-slate-300 animate-spin" />
              ) : (
                <User className="w-5 h-5 text-slate-300" />
              )}
            </div>
            <div className="overflow-hidden">
              <p className="font-medium text-sm truncate">{displayName}</p>
              <p className="text-xs text-slate-400 truncate">
                {user?.email || "Laden..."}
              </p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-4 py-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition"
          >
            <LogOut className="w-5 h-5" />
            Abmelden
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="lg:pl-64">
        {/* Top Header */}
        <header className="sticky top-0 z-30 bg-white border-b border-slate-200">
          <div className="flex items-center justify-between px-4 py-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden text-slate-600 hover:text-slate-900"
            >
              <Menu className="w-6 h-6" />
            </button>
            
            <div className="flex items-center gap-4">
              {/* Breadcrumb could go here */}
            </div>

            <div className="flex items-center gap-4">
              {user?.company_name && (
                <span className="text-sm text-slate-500 hidden md:block">
                  {user.company_name}
                </span>
              )}
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="p-4 md:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
