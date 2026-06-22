"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDateTime, getStatusColor } from "@/lib/utils";
import { Headphones, Calendar, Loader2 } from "lucide-react";

export default function PatientAppointmentsPage() {
  const router = useRouter();
  const { accessToken } = useAuthStore();
  const [appointments, setAppointments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (accessToken) {
      api.get<any[]>("/appointments/my", accessToken)
        .then(setAppointments)
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [accessToken]);

  if (loading) {
    return <div className="flex items-center justify-center h-48"><Loader2 className="animate-spin" /></div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">My Appointments</h1>
        <p className="text-muted-foreground">View and manage your consultations</p>
      </div>

      {appointments.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <Calendar className="w-12 h-12 mx-auto text-muted-foreground mb-3" />
            <p className="text-muted-foreground">No appointments yet</p>
            <Link href="/patient/providers">
              <Button className="mt-4">Book Your First Consultation</Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {appointments.map((appt) => (
            <Card key={appt.id} className="hover:shadow-sm transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-semibold">{appt.practitioner_name || "Doctor"}</p>
                    <p className="text-sm text-muted-foreground">
                      {appt.slot_start ? formatDateTime(appt.slot_start) : "Scheduled"}
                    </p>
                    {appt.chief_complaint && (
                      <p className="text-sm text-muted-foreground mt-1 truncate">{appt.chief_complaint}</p>
                    )}
                  </div>
                  <div className="flex flex-col items-end gap-2 shrink-0">
                    <Badge className={getStatusColor(appt.status)}>{appt.status.replace(/_/g, " ")}</Badge>
                    {["booked", "confirmed", "in_progress"].includes(
                      String(appt.status ?? "").toLowerCase(),
                    ) && (
                      <Button
                        type="button"
                        size="sm"
                        onClick={() => {
                          if (appt.id) {
                            router.push(
                              `/patient/audio-consult?appointmentId=${encodeURIComponent(appt.id)}`,
                            );
                          }
                        }}
                        disabled={!appt.id}
                        title="Start AI voice visit (demo) for this appointment"
                      >
                        <Headphones className="w-3 h-3 mr-1" />
                        Join
                      </Button>
                    )}
                    {appt.status === "completed" && appt.encounter_id && (
                      <Button size="sm" variant="outline" asChild>
                        <Link href="/patient/records">View Records</Link>
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
