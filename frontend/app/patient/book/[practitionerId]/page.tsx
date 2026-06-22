"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/toaster";
import { formatDate, formatTime, formatCurrency, SPECIALTY_LABELS } from "@/lib/utils";
import { Calendar, Clock, ChevronLeft, ChevronRight, CheckCircle, Loader2, AlertCircle } from "lucide-react";
import { format, addDays, startOfDay } from "date-fns";

type Step = "slots" | "questionnaire" | "consent" | "payment" | "confirm";

export default function BookAppointmentPage() {
  const params = useParams();
  const router = useRouter();
  const { accessToken } = useAuthStore();
  const { toast } = useToast();
  const practitionerId = params.practitionerId as string;

  const [practitioner, setPractitioner] = useState<any>(null);
  const [slots, setSlots] = useState<any[]>([]);
  const [selectedSlot, setSelectedSlot] = useState<any>(null);
  const [selectedDate, setSelectedDate] = useState(() => addDays(startOfDay(new Date()), 1));
  const [step, setStep] = useState<Step>("slots");
  const [chiefComplaint, setChiefComplaint] = useState("");
  const [questAnswers, setQuestAnswers] = useState<Record<string, any>>({});
  const [consentAccepted, setConsentAccepted] = useState(false);
  const [consentVersions, setConsentVersions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingSlots, setLoadingSlots] = useState(false);

  useEffect(() => {
    if (practitionerId && accessToken) {
      api.get<any>(`/practitioners/${practitionerId}`, accessToken).then(setPractitioner).catch(console.error);
      api.get<any[]>("/consent/versions", accessToken).then(setConsentVersions).catch(console.error);
    }
  }, [practitionerId, accessToken]);

  useEffect(() => {
    if (practitionerId) {
      setLoadingSlots(true);
      const dateStr = format(selectedDate, "yyyy-MM-dd");
      const nextDay = format(addDays(selectedDate, 1), "yyyy-MM-dd");
      const params = new URLSearchParams({
        date_from: `${dateStr}T00:00:00.000Z`,
        date_to: `${nextDay}T00:00:00.000Z`,
      });
      api
        .get<any[]>(`/practitioners/${practitionerId}/slots?${params.toString()}`, accessToken)
        .then(setSlots)
        .catch(console.error)
        .finally(() => setLoadingSlots(false));
    }
  }, [practitionerId, selectedDate, accessToken]);

  async function handleBook() {
    if (!selectedSlot) return;
    setLoading(true);
    try {
      // Accept consents
      for (const cv of consentVersions) {
        await api.post(`/consent/accept?version_id=${cv.id}`, null, accessToken);
      }

      const appt = await api.post<any>(
        "/appointments/",
        {
          practitioner_id: practitionerId,
          slot_id: selectedSlot.id,
          chief_complaint: chiefComplaint,
          questionnaire_answers: questAnswers,
        },
        accessToken,
      );

      // Mock payment for non-zero fee
      if (practitioner.consultation_fee > 0) {
        const order = await api.post<any>(
          "/appointments/payment/initiate",
          { appointment_id: appt.id, amount: practitioner.consultation_fee },
          accessToken,
        );
        await api.post<any>(
          "/appointments/payment/confirm",
          {
            appointment_id: appt.id,
            payment_reference: order.order_id,
            amount_paid: practitioner.consultation_fee,
          },
          accessToken,
        );
      }

      setStep("confirm");
      toast({ title: "Appointment booked!", description: "You'll receive a reminder before the consultation." });
    } catch (err: any) {
      toast({ title: "Booking failed", description: err.message, variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }

  const dateSlots = slots.filter((s) => {
    const st = new Date(s.start_time);
    return format(st, "yyyy-MM-dd") === format(selectedDate, "yyyy-MM-dd");
  });
  const dates = Array.from({ length: 7 }, (_, i) => addDays(new Date(), i + 1));

  if (!practitioner) {
    return (
      <div className="flex items-center justify-center h-48">
        <Loader2 className="animate-spin" />
      </div>
    );
  }

  if (step === "confirm") {
    return (
      <div className="max-w-md mx-auto text-center space-y-6 py-12">
        <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto">
          <CheckCircle className="w-10 h-10 text-green-600" />
        </div>
        <div>
          <h2 className="text-2xl font-bold">Booking Confirmed!</h2>
          <p className="text-muted-foreground mt-2">
            Your appointment with Dr. {practitioner.first_name} {practitioner.last_name} has been booked.
          </p>
          <p className="text-sm text-muted-foreground mt-1">
            You'll receive a reminder 30 minutes before the consultation.
          </p>
        </div>
        <Button className="w-full" onClick={() => router.push("/patient/appointments")}>
          View My Appointments
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <button onClick={() => router.back()} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ChevronLeft className="w-4 h-4" /> Back
      </button>

      {/* Doctor card */}
      <Card>
        <CardContent className="p-4 flex items-center gap-4">
          <div className="w-14 h-14 rounded-full bg-gradient-to-br from-sky-400 to-blue-600 flex items-center justify-center text-white text-lg font-bold">
            {practitioner.first_name[0]}{practitioner.last_name[0]}
          </div>
          <div>
            <h2 className="font-semibold">Dr. {practitioner.first_name} {practitioner.last_name}</h2>
            <p className="text-sm text-muted-foreground">{SPECIALTY_LABELS[practitioner.specialty]}</p>
            <p className="text-primary font-medium text-sm">
              {practitioner.consultation_fee > 0 ? formatCurrency(practitioner.consultation_fee) : "Free"}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Progress */}
      <div className="flex items-center gap-1">
        {["slots", "questionnaire", "consent", "payment"].map((s, i) => (
          <div key={s} className="flex items-center gap-1 flex-1">
            <div className={`h-1.5 rounded-full flex-1 transition-colors ${
              ["slots", "questionnaire", "consent", "payment"].indexOf(step) >= i ? "bg-primary" : "bg-muted"
            }`} />
          </div>
        ))}
      </div>

      {step === "slots" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Select Date & Time</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Date selector */}
            <div className="flex gap-2 overflow-x-auto pb-1">
              {dates.map((d) => {
                const active = format(d, "yyyy-MM-dd") === format(selectedDate, "yyyy-MM-dd");
                return (
                  <button
                    key={d.toISOString()}
                    onClick={() => setSelectedDate(d)}
                    className={`flex flex-col items-center px-4 py-3 rounded-xl border transition-colors min-w-[64px] ${
                      active ? "bg-primary text-white border-primary" : "hover:bg-muted"
                    }`}
                  >
                    <span className="text-xs">{format(d, "EEE")}</span>
                    <span className="text-lg font-bold">{format(d, "d")}</span>
                  </button>
                );
              })}
            </div>

            {/* Slots */}
            {loadingSlots ? (
              <div className="flex items-center gap-2 text-muted-foreground text-sm">
                <Loader2 className="animate-spin w-4 h-4" /> Loading slots...
              </div>
            ) : dateSlots.length === 0 ? (
              <p className="text-muted-foreground text-sm">No slots available for this date.</p>
            ) : (
              <div className="grid grid-cols-4 gap-2">
                {dateSlots.map((slot) => (
                  <button
                    key={slot.id}
                    onClick={() => setSelectedSlot(slot)}
                    className={`py-2 px-1 text-sm rounded-lg border transition-colors ${
                      selectedSlot?.id === slot.id
                        ? "bg-primary text-white border-primary"
                        : "hover:bg-muted"
                    }`}
                  >
                    {formatTime(slot.start_time)}
                  </button>
                ))}
              </div>
            )}

            <Button
              disabled={!selectedSlot}
              onClick={() => setStep("questionnaire")}
              className="w-full"
            >
              Continue
            </Button>
          </CardContent>
        </Card>
      )}

      {step === "questionnaire" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Pre-Consultation Questions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>What is your main concern today? *</Label>
              <Textarea
                placeholder="Describe your symptoms or reason for consultation..."
                value={chiefComplaint}
                onChange={(e) => setChiefComplaint(e.target.value)}
                className="mt-1"
                rows={3}
              />
            </div>
            <div>
              <Label>How long have you had this issue?</Label>
              <div className="grid grid-cols-2 gap-2 mt-1">
                {["Less than 1 day", "1-3 days", "4-7 days", "More than 1 week"].map((opt) => (
                  <button
                    key={opt}
                    onClick={() => setQuestAnswers((p) => ({ ...p, duration: opt }))}
                    className={`py-2 px-3 text-sm rounded-lg border transition-colors ${
                      questAnswers.duration === opt ? "bg-primary text-white border-primary" : "hover:bg-muted"
                    }`}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <Label>Current medications (if any)</Label>
              <Textarea
                placeholder="List any medications you're currently taking..."
                value={questAnswers.medications || ""}
                onChange={(e) => setQuestAnswers((p) => ({ ...p, medications: e.target.value }))}
                className="mt-1"
                rows={2}
              />
            </div>
            <div className="flex gap-3">
              <Button variant="outline" onClick={() => setStep("slots")}>Back</Button>
              <Button disabled={!chiefComplaint} onClick={() => setStep("consent")} className="flex-1">
                Continue
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {step === "consent" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Review & Consent</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 max-h-48 overflow-y-auto text-sm text-blue-900">
              <p className="font-semibold mb-2">Telemedicine Consent</p>
              <p>By proceeding, you consent to participating in a teleconsultation as per India's Telemedicine Practice Guidelines 2020. Your health data will be processed under DPDP Act 2023. AI tools assist doctors but all decisions are made by licensed clinicians.</p>
            </div>
            <div className="flex items-start gap-3">
              <input
                type="checkbox"
                id="consent"
                checked={consentAccepted}
                onChange={(e) => setConsentAccepted(e.target.checked)}
                className="mt-1"
              />
              <label htmlFor="consent" className="text-sm">
                I have read and agree to the <strong>Telemedicine Consent</strong> and <strong>Data Processing Consent (DPDP Act 2023)</strong>.
              </label>
            </div>
            <div className="flex gap-3">
              <Button variant="outline" onClick={() => setStep("questionnaire")}>Back</Button>
              <Button disabled={!consentAccepted} onClick={() => setStep("payment")} className="flex-1">
                Agree & Continue
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {step === "payment" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Confirm Booking</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Doctor</span>
                <span>Dr. {practitioner.first_name} {practitioner.last_name}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Date & Time</span>
                <span>{selectedSlot ? `${formatDate(selectedSlot.start_time)} at ${formatTime(selectedSlot.start_time)}` : "-"}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Consultation Fee</span>
                <span className="font-semibold text-primary">
                  {practitioner.consultation_fee > 0 ? formatCurrency(practitioner.consultation_fee) : "Free"}
                </span>
              </div>
            </div>

            {practitioner.consultation_fee > 0 && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 flex items-start gap-2 text-sm">
                <AlertCircle className="w-4 h-4 text-yellow-600 mt-0.5 shrink-0" />
                <p className="text-yellow-800">
                  <strong>Mock Payment Mode:</strong> In development, payment is simulated automatically.
                </p>
              </div>
            )}

            <div className="flex gap-3">
              <Button variant="outline" onClick={() => setStep("consent")}>Back</Button>
              <Button onClick={handleBook} disabled={loading} className="flex-1">
                {loading ? <Loader2 className="animate-spin mr-2 w-4 h-4" /> : null}
                {practitioner.consultation_fee > 0 ? `Pay & Book` : "Confirm Booking"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
