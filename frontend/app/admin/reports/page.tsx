"use client";
import { useEffect, useState } from "react";
import { api, API_BASE_URL } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { getStatusColor, formatDateTime, formatCurrency } from "@/lib/utils";
import { Download, Loader2, Filter } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend
} from "recharts";

export default function AdminReportsPage() {
  const { accessToken } = useAuthStore();
  const [appointments, setAppointments] = useState<any[]>([]);
  const [apptTotal, setApptTotal] = useState(0);
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);

  useEffect(() => {
    if (accessToken) {
      Promise.all([
        api.get<{ items: any[]; total: number }>(`/admin/appointments?page=${page}&per_page=20`, accessToken),
        api.get<any>("/admin/dashboard", accessToken),
      ])
        .then(([appts, m]) => {
          const raw = appts as { items?: unknown[]; total?: number } | unknown[] | undefined;
          const list = Array.isArray(raw) ? raw : Array.isArray((raw as { items?: unknown[] })?.items)
            ? (raw as { items: unknown[] }).items
            : [];
          const total =
            raw && typeof raw === "object" && !Array.isArray(raw) && "total" in raw
              ? Number((raw as { total?: number }).total ?? 0)
              : list.length;
          setAppointments(list as any[]);
          setApptTotal(total);
          setMetrics(m);
        })
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [accessToken, page]);

  const pieData = metrics ? [
    { name: "Completed", value: metrics.completed_consultations, color: "#22c55e" },
    { name: "No-show", value: metrics.no_show_count, color: "#f97316" },
    { name: "Other", value: Math.max(0, metrics.total_appointments - metrics.completed_consultations - metrics.no_show_count), color: "#94a3b8" },
  ] : [];

  if (loading) {
    return <div className="flex items-center justify-center h-48"><Loader2 className="animate-spin" /></div>;
  }

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Reports</h1>
          <p className="text-muted-foreground">Analytics and appointment data</p>
        </div>
        <a href={`${API_BASE_URL}/api/v1/admin/appointments/export`} download="appointments.csv">
          <Button variant="outline" size="sm">
            <Download className="w-4 h-4 mr-2" />
            Export All (CSV)
          </Button>
        </a>
      </div>

      {/* Charts */}
      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader><CardTitle className="text-sm">Appointment Status Distribution</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  dataKey="value"
                  label={({ name, value }) => value > 0 ? `${name}: ${value}` : ""}
                >
                  {pieData.map((entry, index) => (
                    <Cell key={index} fill={entry.color} />
                  ))}
                </Pie>
                <Legend />
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-sm">Key Metrics</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {metrics && [
              { label: "Total Appointments", value: metrics.total_appointments },
              { label: "Completed Consultations", value: metrics.completed_consultations },
              { label: "No-show Rate", value: `${metrics.no_show_rate}%` },
              { label: "Total Revenue", value: formatCurrency(metrics.total_revenue_inr) },
              { label: "Active Clinicians", value: metrics.total_clinicians },
              { label: "Registered Patients", value: metrics.total_patients },
            ].map(({ label, value }) => (
              <div key={label} className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">{label}</span>
                <span className="font-semibold text-sm">{value}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Appointments table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">All Appointments</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-muted-foreground">
                  <th className="text-left py-2 pr-4 font-medium">ID</th>
                  <th className="text-left py-2 pr-4 font-medium">Patient</th>
                  <th className="text-left py-2 pr-4 font-medium">Doctor</th>
                  <th className="text-left py-2 pr-4 font-medium">Status</th>
                  <th className="text-left py-2 pr-4 font-medium">Payment</th>
                  <th className="text-left py-2 font-medium">Date</th>
                </tr>
              </thead>
              <tbody>
                {appointments.map((appt) => (
                  <tr key={appt.id} className="border-b last:border-0 hover:bg-muted/50">
                    <td className="py-2 pr-4 font-mono text-xs text-muted-foreground">{appt.id.slice(0, 8)}</td>
                    <td className="py-2 pr-4">{appt.patient_name || "N/A"}</td>
                    <td className="py-2 pr-4">{appt.practitioner_name || "N/A"}</td>
                    <td className="py-2 pr-4">
                      <Badge className={getStatusColor(appt.status)}>{appt.status.replace(/_/g, " ")}</Badge>
                    </td>
                    <td className="py-2 pr-4">
                      <Badge className={getStatusColor(appt.payment_status)}>{appt.payment_status}</Badge>
                    </td>
                    <td className="py-2 text-xs text-muted-foreground">{formatDateTime(appt.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex justify-between mt-4">
            <Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>
              Previous
            </Button>
            <span className="text-sm text-muted-foreground">Page {page}</span>
            <Button
              variant="outline"
              size="sm"
              disabled={page * 20 >= apptTotal}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
