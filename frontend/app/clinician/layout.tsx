"use client";
import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/lib/store";
import { LayoutDashboard, Calendar, Stethoscope, LogOut, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function ClinicianLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, user, logout } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) router.push("/login");
    else if (user?.role !== "clinician") router.push("/login");
  }, [isAuthenticated, user, router]);

  const navItems = [
    { href: "/clinician/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { href: "/clinician/schedule", label: "Schedule", icon: Calendar },
  ];

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <aside className="hidden md:flex w-56 bg-white border-r flex-col">
        <div className="p-4 border-b">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <Stethoscope className="w-4 h-4 text-white" />
            </div>
            <div>
              <p className="font-semibold text-sm">TeleHealth</p>
              <p className="text-xs text-muted-foreground">Clinician</p>
            </div>
          </div>
        </div>
        <nav className="p-3 flex-1 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  active ? "bg-primary text-white" : "text-muted-foreground hover:bg-muted"
                }`}
              >
                <Icon className="w-4 h-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="p-3 border-t">
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start text-muted-foreground"
            onClick={() => { logout(); router.push("/login"); }}
          >
            <LogOut className="w-4 h-4 mr-2" />
            Logout
          </Button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-h-screen">
        <header className="bg-white border-b px-6 h-14 flex items-center justify-between md:hidden">
          <Link href="/clinician/dashboard" className="font-semibold text-primary">TeleHealth</Link>
          <Button variant="ghost" size="sm" onClick={() => { logout(); router.push("/login"); }}>
            <LogOut className="w-4 h-4" />
          </Button>
        </header>
        <main className="flex-1 p-6 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
