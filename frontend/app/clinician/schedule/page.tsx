"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { getStatusColor, formatTime } from "@/lib/utils";
import { Video, Calendar, Loader2, ChevronLeft, ChevronRight } from "lucide-react";
import { format, addDays, subDays } from "date-fns";

export default function ClinicianSchedulePage() {
  const { accessToken } = useAuthStore();
  const [appointments, setAppointments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState(new Date());

  useEffect(() => {
    if (accessToken) {
      setLoading(true);
      const dateStr = format(selectedDate, "yyyy-MM-dd");
      api.get<any[]>(`/appointments/schedule?date=${dateStr}`, accessToken)
        .then(setAppointments)
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [accessToken, selectedDate]);

  return (
    <div className="space-y-6 max-w-3xl">
      <h1 className="text-2xl font-bold">Schedule</h1>

      {/* Date navigation */}
      <div className="flex items-center gap-4">
        <Button variant="outline" size="sm" onClick={() => setSelectedDate((d) => subDays(d, 1))}>
          <ChevronLeft className="w-4 h-4" />
        </Button>
        <div className="text-center">
          <p className="font-semibold">{format(selectedDate, "EEEE, d MMMM yyyy")}</p>
          {format(selectedDate, "yyyy-MM-dd") === format(new Date(), "yyyy-MM-dd") && (
            <Badge className="text-xs bg-primary text-white">Today</Badge>
          )}
        </div>
        <Button variant="outline" size="sm" onClick={() => setSelectedDate((d) => addDays(d, 1))}>
          <ChevronRight className="w-4 h-4" />
        </Button>
        <Button variant="outline" size="sm" onClick={() => setSelectedDate(new Date())}>
          Today
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48"><Loader2 className="animate-spin" /></div>
      ) : appointments.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <Calendar className="w-12 h-12 mx-auto text-muted-foreground mb-3" />
            <p className="text-muted-foreground">No appointments for this day.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {appointments.map((appt) => (
            <Card key={appt.id} className="hover:shadow-sm transition-shadow">
              <CardContent className="p-4 flex items-center gap-4">
                <div className="text-center w-16 shrink-0">
                  <p className="text-sm font-bold text-primary">
                    {appt.slot_start ? formatTime(appt.slot_start) : "N/A"}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {appt.slot_end ? formatTime(appt.slot_end) : ""}
                  </p>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold">{appt.patient_name || "Patient"}</p>
                  <p className="text-sm text-muted-foreground truncate">{appt.chief_complaint || "Teleconsultation"}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Badge className={getStatusColor(appt.status)}>{appt.status.replace(/_/g, " ")}</Badge>
                  {appt.encounter_id && (
                    <Button size="sm" asChild>
                      <Link href={`/clinician/consult/${appt.encounter_id}`}>
                        <Video className="w-3 h-3 mr-1" />
                        {appt.status === "in_progress" ? "Rejoin" : "Start"}
                      </Link>
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
