"use client";

import { useCallback, useEffect, useState, Fragment } from "react";
import { api, APIError } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/toaster";
import { SPECIALTY_LABELS, formatCurrency, formatDateTime, getStatusColor } from "@/lib/utils";
import { Loader2, Pencil, Plus, Trash2, Ban, ChevronDown, ChevronUp } from "lucide-react";

const SPECIALTIES = [
  "general_practice",
  "dermatology",
  "mental_health",
  "pediatrics",
  "cardiology",
  "orthopedics",
  "other",
];

const APPOINTMENT_STATUSES = [
  "",
  "booked",
  "confirmed",
  "in_progress",
  "completed",
  "no_show",
  "cancelled",
  "rescheduled",
];

type Clinician = {
  id: string;
  first_name: string;
  last_name: string;
  registration_number: string;
  specialty: string;
  consultation_fee: number;
  languages: string[];
  years_of_experience: number;
  slot_duration_minutes: number;
  buffer_minutes: number;
  is_available: boolean;
};

export default function AdminActionsPage() {
  const { accessToken } = useAuthStore();
  const { toast } = useToast();

  const [clinicians, setClinicians] = useState<Clinician[]>([]);
  const [cliniciansLoading, setCliniciansLoading] = useState(true);
  const [showDoctorForm, setShowDoctorForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [doctorSaving, setDoctorSaving] = useState(false);
  const [createForm, setCreateForm] = useState({
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    registration_number: "",
    specialty: "general_practice",
    consultation_fee: 500,
    languages: ["en"],
    years_of_experience: 0,
    slot_duration_minutes: 15,
    buffer_minutes: 5,
  });
  const [editForm, setEditForm] = useState({
    first_name: "",
    last_name: "",
    specialty: "general_practice",
    consultation_fee: 500,
    languages: ["en"],
    years_of_experience: 0,
    slot_duration_minutes: 15,
    buffer_minutes: 5,
    is_available: true,
  });

  const [apptPage, setApptPage] = useState(1);
  const [apptTotal, setApptTotal] = useState(0);
  const [apptStatus, setApptStatus] = useState("");
  const [apptDateFrom, setApptDateFrom] = useState("");
  const [apptDateTo, setApptDateTo] = useState("");
  const [appointments, setAppointments] = useState<any[]>([]);
  const [apptLoading, setApptLoading] = useState(true);

  const [sumPage, setSumPage] = useState(1);
  const [sumTotal, setSumTotal] = useState(0);
  const [summaries, setSummaries] = useState<any[]>([]);
  const [sumLoading, setSumLoading] = useState(true);
  const [expandedSummaryId, setExpandedSummaryId] = useState<string | null>(null);

  const loadClinicians = useCallback(() => {
    if (!accessToken) return;
    setCliniciansLoading(true);
    api
      .get<Clinician[]>("/admin/clinicians", accessToken)
      .then((data) => setClinicians(Array.isArray(data) ? data : []))
      .catch(console.error)
      .finally(() => setCliniciansLoading(false));
  }, [accessToken]);

  const loadAppointments = useCallback(() => {
    if (!accessToken) return;
    setApptLoading(true);
    const params = new URLSearchParams({ page: String(apptPage), per_page: "20" });
    if (apptStatus) params.set("status", apptStatus);
    if (apptDateFrom) params.set("date_from", apptDateFrom);
    if (apptDateTo) params.set("date_to", apptDateTo);
    api
      .get<{ items: any[]; total: number }>(`/admin/appointments?${params}`, accessToken)
      .then((d) => {
        const raw = d as { items?: any[]; total?: number } | any[] | undefined;
        const items = Array.isArray(raw) ? raw : Array.isArray((raw as { items?: any[] })?.items)
          ? (raw as { items: any[] }).items
          : [];
        const total =
          raw && typeof raw === "object" && !Array.isArray(raw) && typeof (raw as { total?: number }).total === "number"
            ? (raw as { total: number }).total
            : items.length;
        setAppointments(items);
        setApptTotal(total);
      })
      .catch(console.error)
      .finally(() => setApptLoading(false));
  }, [accessToken, apptPage, apptStatus, apptDateFrom, apptDateTo]);

  const loadSummaries = useCallback(() => {
    if (!accessToken) return;
    setSumLoading(true);
    api
      .get<{ items: any[]; total: number }>(`/admin/summaries?page=${sumPage}&per_page=20`, accessToken)
      .then((d) => {
        const raw = d as { items?: any[]; total?: number } | any[] | undefined;
        const items = Array.isArray(raw) ? raw : Array.isArray((raw as { items?: any[] })?.items)
          ? (raw as { items: any[] }).items
          : [];
        const total =
          raw && typeof raw === "object" && !Array.isArray(raw) && typeof (raw as { total?: number }).total === "number"
            ? (raw as { total: number }).total
            : items.length;
        setSummaries(items);
        setSumTotal(total);
      })
      .catch(console.error)
      .finally(() => setSumLoading(false));
  }, [accessToken, sumPage]);

  useEffect(() => {
    loadClinicians();
  }, [loadClinicians]);

  useEffect(() => {
    loadAppointments();
  }, [loadAppointments]);

  useEffect(() => {
    loadSummaries();
  }, [loadSummaries]);

  async function handleCreateDoctor() {
    setDoctorSaving(true);
    try {
      const newDoc = await api.post<Clinician>("/admin/clinicians", createForm, accessToken);
      setClinicians((prev) => [...prev, newDoc]);
      setShowDoctorForm(false);
      setCreateForm({
        email: "",
        password: "",
        first_name: "",
        last_name: "",
        registration_number: "",
        specialty: "general_practice",
        consultation_fee: 500,
        languages: ["en"],
        years_of_experience: 0,
        slot_duration_minutes: 15,
        buffer_minutes: 5,
      });
      toast({ title: "Doctor added", description: `${newDoc.first_name} ${newDoc.last_name} can sign in.` });
    } catch (err: unknown) {
      const msg = err instanceof APIError ? err.message : "Failed to create";
      toast({ title: "Error", description: msg, variant: "destructive" });
    } finally {
      setDoctorSaving(false);
    }
  }

  function startEdit(doc: Clinician) {
    setEditingId(doc.id);
    setEditForm({
      first_name: doc.first_name,
      last_name: doc.last_name,
      specialty: doc.specialty,
      consultation_fee: doc.consultation_fee,
      languages: doc.languages?.length ? doc.languages : ["en"],
      years_of_experience: doc.years_of_experience,
      slot_duration_minutes: doc.slot_duration_minutes,
      buffer_minutes: doc.buffer_minutes,
      is_available: doc.is_available,
    });
    setShowDoctorForm(false);
  }

  async function handleSaveEdit() {
    if (!editingId || !accessToken) return;
    setDoctorSaving(true);
    try {
      const updated = await api.put<Clinician>(
        `/admin/clinicians/${editingId}`,
        {
          first_name: editForm.first_name,
          last_name: editForm.last_name,
          specialty: editForm.specialty,
          consultation_fee: editForm.consultation_fee,
          languages: editForm.languages,
          years_of_experience: editForm.years_of_experience,
          slot_duration_minutes: editForm.slot_duration_minutes,
          buffer_minutes: editForm.buffer_minutes,
          is_available: editForm.is_available,
        },
        accessToken,
      );
      setClinicians((prev) => prev.map((c) => (c.id === editingId ? updated : c)));
      setEditingId(null);
      toast({ title: "Doctor updated" });
    } catch (err: unknown) {
      const msg = err instanceof APIError ? err.message : "Failed to update";
      toast({ title: "Error", description: msg, variant: "destructive" });
    } finally {
      setDoctorSaving(false);
    }
  }

  async function handleDeactivateDoctor(id: string, force = false) {
    if (!accessToken) return;
    if (!force) {
      if (!window.confirm("Deactivate this doctor? They will not be able to sign in.")) {
        return;
      }
    }
    try {
      const q = force ? "?force=true" : "";
      await api.delete(`/admin/clinicians/${id}${q}`, accessToken);
      loadClinicians();
      toast({ title: "Doctor deactivated" });
    } catch (err: unknown) {
      if (err instanceof APIError && err.status === 400 && !force) {
        if (
          window.confirm(
            "This doctor has upcoming appointments. Force deactivate anyway? (Appointments are not auto-cancelled.)",
          )
        ) {
          await handleDeactivateDoctor(id, true);
        }
        return;
      }
      const msg = err instanceof APIError ? err.message : "Failed to deactivate";
      toast({ title: "Error", description: msg, variant: "destructive" });
    }
  }

  async function handleCancelAppointment(id: string) {
    if (!accessToken) return;
    const reason = window.prompt("Cancellation reason (optional):") ?? "";
    try {
      await api.post(`/admin/appointments/${id}/cancel`, { cancellation_reason: reason || null }, accessToken);
      loadAppointments();
      toast({ title: "Appointment cancelled" });
    } catch (err: unknown) {
      const msg = err instanceof APIError ? err.message : "Failed to cancel";
      toast({ title: "Error", description: msg, variant: "destructive" });
    }
  }

  const canCancelAppt = (status: string) =>
    !["completed", "cancelled", "no_show"].includes(status);

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="text-2xl font-bold">Admin actions</h1>
        <p className="text-muted-foreground">Manage doctors, appointments, and visit summaries</p>
      </div>

      <Tabs defaultValue="doctors" className="w-full">
        <TabsList className="flex flex-wrap h-auto gap-1">
          <TabsTrigger value="doctors">Doctors</TabsTrigger>
          <TabsTrigger value="appointments">Appointments</TabsTrigger>
          <TabsTrigger value="summaries">Summaries</TabsTrigger>
        </TabsList>

        <TabsContent value="doctors" className="space-y-4 mt-4">
          <div className="flex flex-wrap gap-2 justify-between items-center">
            <Button
              variant={showDoctorForm ? "secondary" : "default"}
              onClick={() => {
                setShowDoctorForm(!showDoctorForm);
                setEditingId(null);
              }}
            >
              <Plus className="w-4 h-4 mr-2" />
              Add doctor
            </Button>
          </div>

          {editingId && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Edit doctor</CardTitle>
              </CardHeader>
              <CardContent className="grid sm:grid-cols-2 gap-4">
                {(
                  [
                    { key: "first_name", label: "First name", type: "text" },
                    { key: "last_name", label: "Last name", type: "text" },
                    { key: "consultation_fee", label: "Fee (₹)", type: "number" },
                    { key: "years_of_experience", label: "Years experience", type: "number" },
                    { key: "slot_duration_minutes", label: "Slot duration (min)", type: "number" },
                    { key: "buffer_minutes", label: "Buffer (min)", type: "number" },
                  ] as const
                ).map(({ key, label, type }) => (
                  <div key={key}>
                    <Label>{label}</Label>
                    <Input
                      type={type}
                      className="mt-1"
                      value={(editForm as any)[key]}
                      onChange={(e) =>
                        setEditForm((p) => ({
                          ...p,
                          [key]: type === "number" ? Number(e.target.value) : e.target.value,
                        }))
                      }
                    />
                  </div>
                ))}
                <div>
                  <Label>Specialty</Label>
                  <select
                    className="mt-1 w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
                    value={editForm.specialty}
                    onChange={(e) => setEditForm((p) => ({ ...p, specialty: e.target.value }))}
                  >
                    {SPECIALTIES.map((s) => (
                      <option key={s} value={s}>
                        {SPECIALTY_LABELS[s] || s}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex items-center gap-2 pt-6">
                  <input
                    type="checkbox"
                    id="avail"
                    checked={editForm.is_available}
                    onChange={(e) => setEditForm((p) => ({ ...p, is_available: e.target.checked }))}
                  />
                  <Label htmlFor="avail">Available for booking</Label>
                </div>
                <div className="sm:col-span-2 flex gap-2">
                  <Button variant="outline" onClick={() => setEditingId(null)}>
                    Cancel
                  </Button>
                  <Button onClick={handleSaveEdit} disabled={doctorSaving}>
                    {doctorSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : "Save"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {showDoctorForm && !editingId && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">New doctor</CardTitle>
              </CardHeader>
              <CardContent className="grid sm:grid-cols-2 gap-4">
                {(
                  [
                    { key: "first_name", label: "First name", type: "text" },
                    { key: "last_name", label: "Last name", type: "text" },
                    { key: "email", label: "Email", type: "email" },
                    { key: "password", label: "Temporary password", type: "password" },
                    { key: "registration_number", label: "Medical reg. #", type: "text" },
                    { key: "consultation_fee", label: "Fee (₹)", type: "number" },
                    { key: "years_of_experience", label: "Years experience", type: "number" },
                    { key: "slot_duration_minutes", label: "Slot duration (min)", type: "number" },
                  ] as const
                ).map(({ key, label, type }) => (
                  <div key={key}>
                    <Label>{label}</Label>
                    <Input
                      type={type}
                      className="mt-1"
                      value={(createForm as any)[key]}
                      onChange={(e) =>
                        setCreateForm((p) => ({
                          ...p,
                          [key]: type === "number" ? Number(e.target.value) : e.target.value,
                        }))
                      }
                    />
                  </div>
                ))}
                <div>
                  <Label>Specialty</Label>
                  <select
                    className="mt-1 w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
                    value={createForm.specialty}
                    onChange={(e) => setCreateForm((p) => ({ ...p, specialty: e.target.value }))}
                  >
                    {SPECIALTIES.map((s) => (
                      <option key={s} value={s}>
                        {SPECIALTY_LABELS[s] || s}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="sm:col-span-2 flex gap-2">
                  <Button variant="outline" onClick={() => setShowDoctorForm(false)}>
                    Close
                  </Button>
                  <Button onClick={handleCreateDoctor} disabled={doctorSaving}>
                    {doctorSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : "Create"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {cliniciansLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="animate-spin w-8 h-8" />
            </div>
          ) : (
            <div className="grid gap-3">
              {clinicians.map((doc) => (
                <Card key={doc.id}>
                  <CardContent className="p-4 flex flex-wrap items-center gap-3 justify-between">
                    <div>
                      <p className="font-semibold">
                        Dr. {doc.first_name} {doc.last_name}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {SPECIALTY_LABELS[doc.specialty] || doc.specialty} · Reg. {doc.registration_number} ·{" "}
                        {formatCurrency(doc.consultation_fee)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={doc.is_available ? "default" : "secondary"}>
                        {doc.is_available ? "Active" : "Inactive"}
                      </Badge>
                      <Button size="sm" variant="outline" onClick={() => startEdit(doc)}>
                        <Pencil className="w-4 h-4 mr-1" />
                        Edit
                      </Button>
                      <Button size="sm" variant="destructive" onClick={() => handleDeactivateDoctor(doc.id)}>
                        <Trash2 className="w-4 h-4 mr-1" />
                        Remove
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="appointments" className="space-y-4 mt-4">
          <Card>
            <CardContent className="pt-6 flex flex-wrap gap-3 items-end">
              <div>
                <Label className="text-xs">Status</Label>
                <select
                  className="mt-1 block h-10 rounded-md border border-input bg-background px-3 text-sm min-w-[140px]"
                  value={apptStatus}
                  onChange={(e) => {
                    setApptStatus(e.target.value);
                    setApptPage(1);
                  }}
                >
                  {APPOINTMENT_STATUSES.map((s) => (
                    <option key={s || "all"} value={s}>
                      {s ? s.replace(/_/g, " ") : "All"}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <Label className="text-xs">From (date)</Label>
                <Input
                  type="date"
                  className="mt-1 w-[160px]"
                  value={apptDateFrom}
                  onChange={(e) => {
                    setApptDateFrom(e.target.value);
                    setApptPage(1);
                  }}
                />
              </div>
              <div>
                <Label className="text-xs">To (date)</Label>
                <Input
                  type="date"
                  className="mt-1 w-[160px]"
                  value={apptDateTo}
                  onChange={(e) => {
                    setApptDateTo(e.target.value);
                    setApptPage(1);
                  }}
                />
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="mb-0.5"
                onClick={() => {
                  setApptStatus("");
                  setApptDateFrom("");
                  setApptDateTo("");
                  setApptPage(1);
                }}
              >
                Clear filters
              </Button>
            </CardContent>
          </Card>

          {apptLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="animate-spin w-8 h-8" />
            </div>
          ) : (
            <Card>
              <CardContent className="p-0 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-muted/50 text-muted-foreground text-left">
                      <th className="p-3 font-medium">When</th>
                      <th className="p-3 font-medium">Patient</th>
                      <th className="p-3 font-medium">Doctor</th>
                      <th className="p-3 font-medium">Status</th>
                      <th className="p-3 font-medium">Complaint</th>
                      <th className="p-3 font-medium w-[100px]" />
                    </tr>
                  </thead>
                  <tbody>
                    {appointments.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="p-8 text-center text-muted-foreground">
                          No appointments match your filters.
                        </td>
                      </tr>
                    ) : (
                      appointments.map((appt) => (
                        <tr key={appt.id} className="border-b last:border-0 hover:bg-muted/30">
                          <td className="p-3 whitespace-nowrap">
                            {appt.slot_start ? formatDateTime(appt.slot_start) : "—"}
                          </td>
                          <td className="p-3">{appt.patient_name ?? "—"}</td>
                          <td className="p-3">{appt.practitioner_name ?? "—"}</td>
                          <td className="p-3">
                            <Badge className={getStatusColor(appt.status)}>{appt.status.replace(/_/g, " ")}</Badge>
                          </td>
                          <td className="p-3 max-w-[200px] truncate" title={appt.chief_complaint ?? ""}>
                            {appt.chief_complaint ?? "—"}
                          </td>
                          <td className="p-3">
                            {canCancelAppt(appt.status) ? (
                              <Button size="sm" variant="outline" onClick={() => handleCancelAppointment(appt.id)}>
                                <Ban className="w-3 h-3 mr-1" />
                                Cancel
                              </Button>
                            ) : (
                              <span className="text-muted-foreground text-xs">—</span>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </CardContent>
              <CardContent className="flex justify-between items-center pt-2 border-t">
                <Button variant="outline" size="sm" disabled={apptPage <= 1} onClick={() => setApptPage((p) => p - 1)}>
                  Previous
                </Button>
                <span className="text-sm text-muted-foreground">
                  Page {apptPage} · {apptTotal} total
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={apptPage * 20 >= apptTotal}
                  onClick={() => setApptPage((p) => p + 1)}
                >
                  Next
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="summaries" className="space-y-4 mt-4">
          {sumLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="animate-spin w-8 h-8" />
            </div>
          ) : (
            <Card>
              <CardContent className="p-0 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-muted/50 text-muted-foreground text-left">
                      <th className="p-3 w-8" />
                      <th className="p-3 font-medium">Date</th>
                      <th className="p-3 font-medium">Patient</th>
                      <th className="p-3 font-medium">Doctor</th>
                      <th className="p-3 font-medium">Status</th>
                      <th className="p-3 font-medium">Diagnosis / summary</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summaries.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="p-8 text-center text-muted-foreground">
                          No visit records yet.
                        </td>
                      </tr>
                    ) : (
                      summaries.map((row) => (
                        <Fragment key={row.id}>
                          <tr className="border-b hover:bg-muted/30">
                            <td className="p-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0"
                                onClick={() =>
                                  setExpandedSummaryId((id) => (id === row.id ? null : row.id))
                                }
                              >
                                {expandedSummaryId === row.id ? (
                                  <ChevronUp className="w-4 h-4" />
                                ) : (
                                  <ChevronDown className="w-4 h-4" />
                                )}
                              </Button>
                            </td>
                            <td className="p-3 whitespace-nowrap">{formatDateTime(row.created_at)}</td>
                            <td className="p-3">{row.patient_name ?? "—"}</td>
                            <td className="p-3">{row.practitioner_name ?? "—"}</td>
                            <td className="p-3">
                              <Badge variant="outline">{row.status}</Badge>
                            </td>
                            <td className="p-3 max-w-[280px] truncate" title={row.diagnosis ?? ""}>
                              {row.diagnosis ?? "—"}
                            </td>
                          </tr>
                          {expandedSummaryId === row.id && (
                            <tr key={`${row.id}-detail`} className="bg-muted/20 border-b">
                              <td colSpan={6} className="p-4">
                                <p className="text-xs font-medium text-muted-foreground mb-1">Notes</p>
                                <p className="whitespace-pre-wrap text-sm">{row.notes || "—"}</p>
                                {row.encounter_id && (
                                  <p className="text-xs text-muted-foreground mt-2">Encounter: {row.encounter_id}</p>
                                )}
                              </td>
                            </tr>
                          )}
                        </Fragment>
                      ))
                    )}
                  </tbody>
                </table>
              </CardContent>
              <CardContent className="flex justify-between items-center pt-2 border-t">
                <Button variant="outline" size="sm" disabled={sumPage <= 1} onClick={() => setSumPage((p) => p - 1)}>
                  Previous
                </Button>
                <span className="text-sm text-muted-foreground">
                  Page {sumPage} · {sumTotal} total
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={sumPage * 20 >= sumTotal}
                  onClick={() => setSumPage((p) => p + 1)}
                >
                  Next
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
