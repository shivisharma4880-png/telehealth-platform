"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDateTime, getStatusColor, SPECIALTY_LABELS, formatCurrency } from "@/lib/utils";
import { Calendar, Stethoscope, FileText, Plus, Headphones } from "lucide-react";

export default function PatientHomePage() {
  const router = useRouter();
  const { accessToken, user } = useAuthStore();
  const [appointments, setAppointments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (accessToken) {
      api.get<any[]>("/appointments/my", accessToken)
        .then((data) => setAppointments(data.slice(0, 3)))
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [accessToken]);

  const upcomingAppts = appointments.filter((a) =>
    ["booked", "confirmed", "in_progress"].includes(String(a.status ?? "").toLowerCase()),
  );

  return (
    <div className="space-y-6">
      {/* Welcome */}
      <div className="bg-gradient-to-r from-sky-500 to-blue-600 rounded-2xl p-6 text-white">
        <p className="opacity-80 text-sm">Good morning,</p>
        <h1 className="text-2xl font-bold mt-1">Welcome back!</h1>
        <p className="opacity-80 text-sm mt-1">How are you feeling today?</p>
        <Link href="/patient/providers">
          <Button className="mt-4 bg-white text-primary hover:bg-white/90" size="sm">
            <Plus className="w-4 h-4 mr-1" />
            Book Consultation
          </Button>
        </Link>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-2 gap-3">
        <Link href="/patient/providers">
          <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
            <CardContent className="p-4 flex flex-col items-center text-center gap-2">
              <div className="w-12 h-12 bg-sky-100 rounded-xl flex items-center justify-center">
                <Stethoscope className="w-6 h-6 text-sky-600" />
              </div>
              <span className="font-medium text-sm">Find a Doctor</span>
            </CardContent>
          </Card>
        </Link>
        <Link href="/patient/appointments">
          <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
            <CardContent className="p-4 flex flex-col items-center text-center gap-2">
              <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center">
                <Calendar className="w-6 h-6 text-purple-600" />
              </div>
              <span className="font-medium text-sm">My Appointments</span>
            </CardContent>
          </Card>
        </Link>
        <Link href="/patient/records">
          <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
            <CardContent className="p-4 flex flex-col items-center text-center gap-2">
              <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
                <FileText className="w-6 h-6 text-green-600" />
              </div>
              <span className="font-medium text-sm">My Records</span>
            </CardContent>
          </Card>
        </Link>
        <Link href="/patient/audio-consult">
          <Card className="hover:shadow-md transition-shadow cursor-pointer h-full border-emerald-200 bg-emerald-50/40">
            <CardContent className="p-4 flex flex-col items-center text-center gap-2">
              <div className="w-12 h-12 bg-emerald-100 rounded-xl flex items-center justify-center">
                <Headphones className="w-6 h-6 text-emerald-700" />
              </div>
              <span className="font-medium text-sm">AI voice triage (demo)</span>
            </CardContent>
          </Card>
        </Link>
      </div>

      {/* Upcoming appointments */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-lg">Upcoming</h2>
          <Link href="/patient/appointments" className="text-sm text-primary hover:underline">
            View all
          </Link>
        </div>

        {loading ? (
          <Card><CardContent className="p-8 text-center text-muted-foreground">Loading...</CardContent></Card>
        ) : upcomingAppts.length === 0 ? (
          <Card>
            <CardContent className="p-8 text-center">
              <Calendar className="w-12 h-12 mx-auto text-muted-foreground mb-3" />
              <p className="text-muted-foreground">No upcoming appointments</p>
              <Link href="/patient/providers">
                <Button className="mt-3" size="sm">Book a Consultation</Button>
              </Link>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {upcomingAppts.map((appt) => (
              <Card key={appt.id} className="hover:shadow-sm transition-shadow">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">{appt.practitioner_name || "Doctor"}</p>
                      <p className="text-sm text-muted-foreground">
                        {appt.slot_start ? formatDateTime(appt.slot_start) : "Scheduled"}
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <Badge className={getStatusColor(appt.status)}>{appt.status}</Badge>
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
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
