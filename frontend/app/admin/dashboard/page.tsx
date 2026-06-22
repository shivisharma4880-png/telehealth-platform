"use client";
import { useEffect, useMemo, useState } from "react";
import { api, API_BASE_URL } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatDateTime, getStatusColor, formatCurrency } from "@/lib/utils";
import { Users, Calendar, TrendingUp, UserX, Loader2, Download } from "lucide-react";

const WEEKLY_PLACEHOLDER = [
  { name: "Mon", consults: 12 },
  { name: "Tue", consults: 18 },
  { name: "Wed", consults: 15 },
  { name: "Thu", consults: 22 },
  { name: "Fri", consults: 19 },
  { name: "Sat", consults: 8 },
  { name: "Sun", consults: 5 },
];

function normalizeAppointmentList(raw: unknown): any[] {
  if (Array.isArray(raw)) return raw;
  if (raw && typeof raw === "object" && Array.isArray((raw as { items?: unknown[] }).items)) {
    return (raw as { items: any[] }).items;
  }
  return [];
}

function normalizeMetrics(raw: unknown): Record<string, number> {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return {};
  const o = raw as Record<string, unknown>;
  const num = (k: string) => (typeof o[k] === "number" ? (o[k] as number) : Number(o[k]) || 0);
  return {
    total_appointments: num("total_appointments"),
    completed_consultations: num("completed_consultations"),
    no_show_count: num("no_show_count"),
    no_show_rate: num("no_show_rate"),
    total_revenue_inr: num("total_revenue_inr"),
    total_patients: num("total_patients"),
    total_clinicians: num("total_clinicians"),
  };
}

export default function AdminDashboardPage() {
  const { accessToken } = useAuthStore();
  const [metrics, setMetrics] = useState<Record<string, number>>({});
  const [appointments, setAppointments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const chartData = useMemo(() => WEEKLY_PLACEHOLDER, []);
  const maxConsults = useMemo(
    () => Math.max(1, ...chartData.map((d) => d.consults)),
    [chartData],
  );

  useEffect(() => {
    if (!accessToken) return;
    setLoading(true);
    Promise.all([
      api.get<unknown>("/admin/dashboard", accessToken),
      api.get<unknown>("/admin/appointments?per_page=10", accessToken),
    ])
      .then(([m, appts]) => {
        setMetrics(normalizeMetrics(m));
        setAppointments(normalizeAppointmentList(appts));
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [accessToken]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48">
        <Loader2 className="animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Admin Dashboard</h1>
          <p className="text-muted-foreground">Clinic overview and metrics</p>
        </div>
        <a href={`${API_BASE_URL}/api/v1/admin/appointments/export`} download="appointments.csv">
          <Button variant="outline" size="sm">
            <Download className="w-4 h-4 mr-2" />
            Export CSV
          </Button>
        </a>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          {
            label: "Total Consultations",
            value: metrics.completed_consultations || 0,
            icon: Calendar,
            color: "text-blue-600 bg-blue-100",
          },
          {
            label: "Total Patients",
            value: metrics.total_patients || 0,
            icon: Users,
            color: "text-green-600 bg-green-100",
          },
          {
            label: "No-show Rate",
            value: `${metrics.no_show_rate || 0}%`,
            icon: UserX,
            color: "text-orange-600 bg-orange-100",
          },
          {
            label: "Total Revenue",
            value: formatCurrency(metrics.total_revenue_inr || 0),
            icon: TrendingUp,
            color: "text-purple-600 bg-purple-100",
          },
        ].map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.label}>
              <CardContent className="p-4 flex items-center gap-3">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${stat.color} shrink-0`}>
                  <Icon className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-xl font-bold">{stat.value}</p>
                  <p className="text-xs text-muted-foreground">{stat.label}</p>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Consultations This Week (sample)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex h-[200px] items-end justify-between gap-1 border-b border-muted pb-2">
              {chartData.map((d) => (
                <div key={d.name} className="flex flex-1 flex-col items-center gap-1">
                  <div
                    className="w-full max-w-[36px] rounded-t bg-sky-500/90 mx-auto"
                    style={{ height: `${(d.consults / maxConsults) * 140}px`, minHeight: "4px" }}
                    title={`${d.name}: ${d.consults}`}
                  />
                  <span className="text-[10px] text-muted-foreground">{d.name}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              ["Total Appointments", metrics.total_appointments || 0],
              ["Completed", metrics.completed_consultations || 0],
              ["No-shows", metrics.no_show_count || 0],
              ["Active Clinicians", metrics.total_clinicians || 0],
            ].map(([label, value]) => (
              <div key={label as string} className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{label}</span>
                <span className="font-semibold">{value}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Recent Appointments</CardTitle>
        </CardHeader>
        <CardContent>
          {appointments.length === 0 ? (
            <p className="text-muted-foreground text-sm text-center py-4">No appointments yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-muted-foreground">
                    <th className="text-left py-2 pr-4">Patient</th>
                    <th className="text-left py-2 pr-4">Doctor</th>
                    <th className="text-left py-2 pr-4">Status</th>
                    <th className="text-left py-2 pr-4">Payment</th>
                    <th className="text-left py-2">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {appointments.map((appt, idx) => {
                    const status = typeof appt?.status === "string" ? appt.status : "";
                    const payment = typeof appt?.payment_status === "string" ? appt.payment_status : "";
                    return (
                      <tr key={String(appt?.id ?? `appt-${idx}`)} className="border-b last:border-0 hover:bg-muted/50">
                        <td className="py-2 pr-4">{appt.patient_name || "N/A"}</td>
                        <td className="py-2 pr-4">{appt.practitioner_name || "N/A"}</td>
                        <td className="py-2 pr-4">
                          <Badge className={getStatusColor(status)}>{status.replace(/_/g, " ") || "—"}</Badge>
                        </td>
                        <td className="py-2 pr-4">
                          <Badge className={getStatusColor(payment)}>{payment || "—"}</Badge>
                        </td>
                        <td className="py-2">{formatCurrency(Number(appt?.amount_paid) || 0)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
