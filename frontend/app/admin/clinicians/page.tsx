"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/toaster";
import { SPECIALTY_LABELS, formatCurrency } from "@/lib/utils";
import { Plus, Loader2, UserCheck } from "lucide-react";

const SPECIALTIES = [
  "general_practice", "dermatology", "mental_health", "pediatrics", "cardiology", "orthopedics", "other"
];

export default function AdminCliniciansPage() {
  const { accessToken } = useAuthStore();
  const { toast } = useToast();
  const [clinicians, setClinicians] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    email: "", password: "", first_name: "", last_name: "",
    registration_number: "", specialty: "general_practice",
    consultation_fee: 500, languages: ["en"], years_of_experience: 0,
    slot_duration_minutes: 15, buffer_minutes: 5,
  });

  useEffect(() => {
    if (accessToken) {
      api.get<any[]>("/admin/clinicians", accessToken)
        .then((data) => setClinicians(Array.isArray(data) ? data : []))
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [accessToken]);

  async function handleCreate() {
    setSaving(true);
    try {
      const newDoc = await api.post<any>("/admin/clinicians", form, accessToken);
      setClinicians((prev) => [...prev, newDoc]);
      setShowForm(false);
      toast({ title: "Clinician added!", description: `Dr. ${newDoc.first_name} ${newDoc.last_name} can now login.` });
    } catch (err: any) {
      toast({ title: "Error", description: err.message, variant: "destructive" });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Clinicians</h1>
          <p className="text-muted-foreground">Manage your clinic's doctors</p>
        </div>
        <Button onClick={() => setShowForm(!showForm)}>
          <Plus className="w-4 h-4 mr-2" />
          Add Clinician
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardHeader><CardTitle className="text-base">Invite New Clinician</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-2 gap-4">
            {[
              { key: "first_name", label: "First Name", type: "text" },
              { key: "last_name", label: "Last Name", type: "text" },
              { key: "email", label: "Email", type: "email" },
              { key: "password", label: "Temporary Password", type: "password" },
              { key: "registration_number", label: "Medical Reg. Number", type: "text" },
              { key: "consultation_fee", label: "Consultation Fee (₹)", type: "number" },
              { key: "years_of_experience", label: "Years of Experience", type: "number" },
              { key: "slot_duration_minutes", label: "Slot Duration (min)", type: "number" },
            ].map(({ key, label, type }) => (
              <div key={key}>
                <Label>{label}</Label>
                <Input
                  type={type}
                  value={(form as any)[key]}
                  onChange={(e) => setForm((p) => ({ ...p, [key]: type === "number" ? Number(e.target.value) : e.target.value }))}
                  className="mt-1"
                />
              </div>
            ))}
            <div>
              <Label>Specialty</Label>
              <select
                value={form.specialty}
                onChange={(e) => setForm((p) => ({ ...p, specialty: e.target.value }))}
                className="mt-1 w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                {SPECIALTIES.map((s) => (
                  <option key={s} value={s}>{SPECIALTY_LABELS[s] || s}</option>
                ))}
              </select>
            </div>
            <div className="col-span-2 flex gap-3">
              <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
              <Button onClick={handleCreate} disabled={saving}>
                {saving ? <Loader2 className="animate-spin mr-2 w-4 h-4" /> : null}
                Create Account
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-48"><Loader2 className="animate-spin" /></div>
      ) : (
        <div className="grid gap-4">
          {clinicians.map((doc) => (
            <Card key={doc.id}>
              <CardContent className="p-4 flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-sky-400 to-blue-600 flex items-center justify-center text-white font-bold">
                  {doc.first_name[0]}{doc.last_name[0]}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">Dr. {doc.first_name} {doc.last_name}</h3>
                    <UserCheck className="w-4 h-4 text-green-500" />
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {SPECIALTY_LABELS[doc.specialty] || doc.specialty} • Reg. {doc.registration_number}
                  </p>
                  <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                    <span>{doc.years_of_experience}y experience</span>
                    <span>•</span>
                    <span>{doc.slot_duration_minutes}min slots</span>
                    <span>•</span>
                    <span className="text-primary font-medium">{formatCurrency(doc.consultation_fee)}</span>
                  </div>
                </div>
                <Badge variant={doc.is_available ? "default" : "secondary"}>
                  {doc.is_available ? "Available" : "Unavailable"}
                </Badge>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
