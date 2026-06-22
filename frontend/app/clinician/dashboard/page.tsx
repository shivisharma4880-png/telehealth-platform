"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDateTime, getStatusColor } from "@/lib/utils";
import { Video, Calendar, Users, Clock, Loader2, ChevronRight } from "lucide-react";
import { format } from "date-fns";

export default function ClinicianDashboardPage() {
  const { accessToken } = useAuthStore();
  const [appointments, setAppointments] = useState<any[]>([]);
  const [practitioner, setPractitioner] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const today = format(new Date(), "yyyy-MM-dd");

  useEffect(() => {
    if (accessToken) {
      Promise.all([
        api.get<any>("/practitioners/me", accessToken),
        api.get<any[]>(`/appointments/schedule?date=${today}`, accessToken),
      ])
        .then(([prac, appts]) => {
          setPractitioner(prac);
          setAppointments(appts);
        })
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [accessToken, today]);

  const completed = appointments.filter((a) => a.status === "completed").length;
  const upcoming = appointments.filter((a) => ["booked", "confirmed"].includes(a.status)).length;
  const inProgress = appointments.filter((a) => a.status === "in_progress");

  if (loading) {
    return <div className="flex items-center justify-center h-48"><Loader2 className="animate-spin" /></div>;
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold">
          Good morning, {practitioner ? `Dr. ${practitioner.first_name}` : "Doctor"}
        </h1>
        <p className="text-muted-foreground">Here's your schedule for today, {format(new Date(), "EEEE, d MMMM yyyy")}</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Today's Patients", value: appointments.length, icon: Users, color: "text-blue-600 bg-blue-100" },
          { label: "Upcoming", value: upcoming, icon: Calendar, color: "text-purple-600 bg-purple-100" },
          { label: "In Progress", value: inProgress.length, icon: Video, color: "text-amber-600 bg-amber-100" },
          { label: "Completed", value: completed, icon: Clock, color: "text-green-600 bg-green-100" },
        ].map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.label}>
              <CardContent className="p-4 flex items-center gap-3">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${stat.color}`}>
                  <Icon className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stat.value}</p>
                  <p className="text-xs text-muted-foreground">{stat.label}</p>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Active consultation alert */}
      {inProgress.length > 0 && (
        <Card className="border-amber-300 bg-amber-50">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="font-semibold text-amber-800">Consultation In Progress</p>
              <p className="text-sm text-amber-700">{inProgress[0].patient_name} — ongoing</p>
            </div>
            <Button size="sm" className="bg-amber-600 hover:bg-amber-700" asChild>
              <Link href={`/clinician/consult/${inProgress[0].encounter_id}`}>
                <Video className="w-4 h-4 mr-1" />
                Rejoin
              </Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Today's schedule */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Today's Schedule</CardTitle>
            <Link href="/clinician/schedule" className="text-sm text-primary hover:underline flex items-center gap-1">
              Full schedule <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
        </CardHeader>
        <CardContent>
          {appointments.length === 0 ? (
            <p className="text-muted-foreground text-sm text-center py-6">No appointments scheduled for today.</p>
          ) : (
            <div className="space-y-3">
              {appointments.map((appt) => (
                <div key={appt.id} className="flex items-center justify-between py-3 border-b last:border-0">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-sky-400 to-blue-600 flex items-center justify-center text-white text-sm font-bold">
                      {(appt.patient_name || "P").charAt(0)}
                    </div>
                    <div>
                      <p className="font-medium text-sm">{appt.patient_name || "Patient"}</p>
                      <p className="text-xs text-muted-foreground">
                        {appt.slot_start ? format(new Date(appt.slot_start), "hh:mm a") : "N/A"}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className={getStatusColor(appt.status)}>
                      {appt.status.replace(/_/g, " ")}
                    </Badge>
                    {appt.encounter_id && (
                      <Button size="sm" variant={appt.status === "in_progress" ? "default" : "outline"} asChild>
                        <Link href={`/clinician/consult/${appt.encounter_id}`}>
                          <Video className="w-3 h-3 mr-1" />
                          {appt.status === "in_progress" ? "Rejoin" : "Start"}
                        </Link>
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
