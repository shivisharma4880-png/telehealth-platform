"use client";
import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/lib/store";
import { Home, Calendar, FileText, User, LogOut, Stethoscope } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function PatientLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, user, logout } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) router.push("/login");
    else if (user?.role !== "patient") router.push("/login");
  }, [isAuthenticated, user, router]);

  const navItems = [
    { href: "/patient/home", label: "Home", icon: Home },
    { href: "/patient/providers", label: "Doctors", icon: Stethoscope },
    { href: "/patient/appointments", label: "Appointments", icon: Calendar },
    { href: "/patient/records", label: "Records", icon: FileText },
    { href: "/patient/profile", label: "Profile", icon: User },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top navbar */}
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-screen-xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/patient/home" className="flex items-center gap-2 font-semibold text-primary">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <Stethoscope className="w-4 h-4 text-white" />
            </div>
            TeleHealth
          </Link>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => { logout(); router.push("/login"); }}
            className="text-muted-foreground"
          >
            <LogOut className="w-4 h-4 mr-1" />
            Logout
          </Button>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-screen-xl mx-auto px-4 py-6 pb-24">{children}</main>

      {/* Bottom nav (mobile) */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t z-10 md:hidden">
        <div className="flex">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex-1 flex flex-col items-center py-2 text-xs gap-1 transition-colors ${
                  active ? "text-primary" : "text-muted-foreground"
                }`}
              >
                <Icon className="w-5 h-5" />
                {item.label}
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
