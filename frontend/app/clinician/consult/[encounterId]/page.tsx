"use client";
import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, API_BASE_URL } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/components/ui/toaster";
import {
  Loader2, PhoneOff, FileText, Pill,
  Sparkles, CheckCircle, AlertTriangle, Search, Plus, Trash2,
  Eye, Send, Stethoscope,
} from "lucide-react";

export default function ClinicianConsultPage() {
  const params = useParams();
  const router = useRouter();
  const { accessToken } = useAuthStore();
  const { toast } = useToast();
  const encounterId = params.encounterId as string;

  const [encounterLoading, setEncounterLoading] = useState(true);
  const [consultStarted, setConsultStarted] = useState(false);
  const [consultEnded, setConsultEnded] = useState(false);

  // Transcript state
  const [transcriptEnabled, setTranscriptEnabled] = useState(true);
  const [transcriptSegments, setTranscriptSegments] = useState<any[]>([]);
  const transcriptRef = useRef<HTMLDivElement>(null);

  // SOAP notes state
  const [soapNote, setSoapNote] = useState({
    subjective: "", objective: "", assessment: "", plan: "",
    investigations: "", follow_up_notes: ""
  });
  const [noteStatus, setNoteStatus] = useState<"draft" | "final">("draft");
  const [generatingNote, setGeneratingNote] = useState(false);
  const [generatedCount, setGeneratedCount] = useState(0);

  // Prescription state
  const [prescriptionId, setPrescriptionId] = useState<string | null>(null);
  const [diagnosis, setDiagnosis] = useState("");
  const [medications, setMedications] = useState<any[]>([]);
  const [drugSearch, setDrugSearch] = useState("");
  const [drugResults, setDrugResults] = useState<any[]>([]);
  const [searchingDrugs, setSearchingDrugs] = useState(false);
  const [interactionWarnings, setInteractionWarnings] = useState<any[]>([]);
  const [signingRx, setSigningRx] = useState(false);
  const [signedRx, setSignedRx] = useState<any>(null);

  useEffect(() => {
    if (encounterId && accessToken) {
      api
        .get<any>(`/encounters/${encounterId}`, accessToken)
        .then((enc) => {
          if (enc.soap_subjective) {
            setSoapNote({
              subjective: enc.soap_subjective || "",
              objective: enc.soap_objective || "",
              assessment: enc.soap_assessment || "",
              plan: enc.soap_plan || "",
              investigations: enc.investigations || "",
              follow_up_notes: enc.follow_up_notes || "",
            });
          }
          setNoteStatus(enc.soap_note_status || "draft");
          setGeneratedCount(enc.soap_generated_count || 0);
        })
        .catch((err) => toast({ title: "Could not load visit", description: err.message, variant: "destructive" }))
        .finally(() => setEncounterLoading(false));
    }
  }, [encounterId, accessToken, toast]);

  // SSE transcript stream
  useEffect(() => {
    if (!consultStarted || !transcriptEnabled || !accessToken) return;

    const eventSource = new EventSource(
      `${API_BASE_URL}/api/v1/encounters/${encounterId}/transcript/stream`,
    );

    eventSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.event === "end") { eventSource.close(); return; }
        setTranscriptSegments((prev) => [...prev, data]);
      } catch {}
    };

    eventSource.onerror = () => eventSource.close();
    return () => eventSource.close();
  }, [consultStarted, transcriptEnabled, encounterId, accessToken]);

  // Auto-scroll transcript
  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [transcriptSegments]);

  async function handleStartConsult() {
    try {
      await api.post(`/encounters/${encounterId}/start`, null, accessToken);
      setConsultStarted(true);
      toast({ title: "Consultation started", description: "Transcription is active." });
    } catch (err: any) {
      toast({ title: "Error", description: err.message, variant: "destructive" });
    }
  }

  async function handleEndConsult() {
    try {
      const result = await api.post<any>(`/encounters/${encounterId}/end`, null, accessToken);
      setConsultEnded(true);
      setConsultStarted(false);
      toast({ title: "Consultation ended", description: `Duration: ${result.duration_minutes} min` });
    } catch (err: any) {
      toast({ title: "Error", description: err.message, variant: "destructive" });
    }
  }

  async function handleGenerateSOAP() {
    if (generatedCount >= 2) {
      toast({ title: "Limit reached", description: "Maximum 2 SOAP note generations per consult.", variant: "destructive" });
      return;
    }
    setGeneratingNote(true);
    try {
      const result = await api.post<any>(`/encounters/${encounterId}/generate-notes`, null, accessToken);
      setSoapNote({
        subjective: result.note.subjective || "",
        objective: result.note.objective || "",
        assessment: result.note.assessment || "",
        plan: result.note.plan || "",
        investigations: result.note.investigations || "",
        follow_up_notes: result.note.follow_up_notes || "",
      });
      setGeneratedCount(result.generated_count);
      toast({ title: "SOAP note generated", description: result.warning, variant: "default" });
    } catch (err: any) {
      toast({ title: "Generation failed", description: err.message, variant: "destructive" });
    } finally {
      setGeneratingNote(false);
    }
  }

  async function handleSaveSOAP() {
    try {
      await api.patch(`/encounters/${encounterId}/notes`, soapNote, accessToken);
      toast({ title: "Notes saved" });
    } catch (err: any) {
      toast({ title: "Save failed", description: err.message, variant: "destructive" });
    }
  }

  async function handleFinalizeSOAP() {
    try {
      await api.post(`/encounters/${encounterId}/notes/finalize`, soapNote, accessToken);
      setNoteStatus("final");
      toast({ title: "Notes finalized", description: "SOAP notes are now part of the encounter record." });
    } catch (err: any) {
      toast({ title: "Error", description: err.message, variant: "destructive" });
    }
  }

  async function handleDrugSearch(query: string) {
    setDrugSearch(query);
    if (query.length < 2) { setDrugResults([]); return; }
    setSearchingDrugs(true);
    try {
      const results = await api.get<any[]>(`/prescriptions/drugs/search?q=${encodeURIComponent(query)}`, accessToken);
      setDrugResults(results);
    } catch {} finally { setSearchingDrugs(false); }
  }

  function addMedication(drug: any) {
    const newMed = {
      drug_id: drug.id,
      drug_name: drug.name,
      strength: drug.available_strengths?.[0] || "",
      dosage_form: drug.dosage_forms?.[0] || "tablet",
      route: "oral",
      frequency: "Once daily",
      duration: "7 days",
      instructions: "",
    };
    setMedications((prev) => [...prev, newMed]);
    setDrugSearch("");
    setDrugResults([]);
  }

  function updateMedication(index: number, field: string, value: string) {
    setMedications((prev) => prev.map((m, i) => i === index ? { ...m, [field]: value } : m));
  }

  function removeMedication(index: number) {
    setMedications((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleCheckInteractions() {
    const drugIds = medications.filter((m) => m.drug_id).map((m) => m.drug_id);
    if (drugIds.length < 2) { setInteractionWarnings([]); return; }

    try {
      const result = await api.post<any>(
        "/prescriptions/drugs/check-interactions",
        { drug_ids: drugIds },
        accessToken
      );
      setInteractionWarnings(result.warnings);
      if (result.count > 0) {
        toast({ title: `${result.count} interaction(s) found`, description: "Review warnings below.", variant: "destructive" });
      }
    } catch {}
  }

  async function handleSignPrescription() {
    if (medications.length === 0) {
      toast({ title: "No medications added", variant: "destructive" }); return;
    }
    setSigningRx(true);
    try {
      // Create prescription
      const rx = await api.post<any>(
        "/prescriptions/",
        { encounter_id: encounterId, diagnosis, medications },
        accessToken,
      );
      // Sign it
      const signed = await api.post<any>(`/prescriptions/${rx.id}/sign`, null, accessToken);
      setSignedRx(signed);
      setPrescriptionId(rx.id);
      toast({ title: "Prescription signed!", description: "Patient has been notified." });
    } catch (err: any) {
      toast({ title: "Error", description: err.message, variant: "destructive" });
    } finally {
      setSigningRx(false);
    }
  }

  if (encounterLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="animate-spin w-8 h-8 text-primary" />
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden -m-6">
      <div className="flex flex-col bg-slate-900 text-white" style={{ width: "55%" }}>
        <div className="shrink-0 border-b border-white/10 p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Stethoscope className="w-6 h-6 text-sky-400" />
            <div>
              <p className="font-semibold text-sm">Clinician visit workspace</p>
              <p className="text-xs text-white/60">
                Start the visit to enable transcript streaming, then use SOAP and e-prescribe on the right.
              </p>
            </div>
          </div>
          <Button
            type="button"
            size="sm"
            className="w-full sm:w-auto"
            onClick={() => void handleStartConsult()}
            disabled={consultStarted || consultEnded}
          >
            Start visit
          </Button>
        </div>

        {transcriptEnabled && (
          <div className="flex-1 min-h-0 flex flex-col border-t border-white/10">
            <div className="flex items-center justify-between px-3 py-2 border-b border-white/10 shrink-0">
              <span className="text-xs text-white/70 font-medium flex items-center gap-1">
                <div className={`w-1.5 h-1.5 rounded-full ${consultStarted ? "bg-red-500 animate-pulse" : "bg-gray-500"}`} />
                Live transcript
              </span>
              <button
                type="button"
                onClick={() => setTranscriptEnabled(false)}
                className="text-white/50 hover:text-white/80 text-xs"
              >
                Hide
              </button>
            </div>
            <div ref={transcriptRef} className="flex-1 min-h-0 overflow-y-auto p-2 space-y-1">
              {transcriptSegments.length === 0 ? (
                <p className="text-white/40 text-xs text-center py-4">
                  {consultStarted ? "Listening for speech…" : "Start the visit to begin transcription."}
                </p>
              ) : (
                transcriptSegments.map((seg, i) => (
                  <div key={i} className="text-xs">
                    <span className={`font-semibold ${seg.speaker === "clinician" ? "text-sky-400" : "text-green-400"}`}>
                      [{seg.speaker}]:
                    </span>
                    <span className="text-white/80 ml-1">{seg.text}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        <div className="shrink-0 bg-slate-950 px-4 py-3 flex items-center justify-between border-t border-white/10">
          {!transcriptEnabled && (
            <Button
              size="sm"
              variant="outline"
              className="border-white/20 text-white hover:bg-white/10"
              onClick={() => setTranscriptEnabled(true)}
            >
              <Eye className="w-3 h-3 mr-1" /> Show transcript
            </Button>
          )}
          <div className="flex items-center gap-2 ml-auto">
            <Button
              size="sm"
              variant="destructive"
              onClick={handleEndConsult}
              disabled={consultEnded}
              className="bg-red-600 hover:bg-red-700"
            >
              <PhoneOff className="w-4 h-4 mr-1" />
              End consult
            </Button>
          </div>
        </div>
      </div>

      {/* Right panel — notes & prescription */}
      <div className="flex-1 bg-white flex flex-col overflow-hidden border-l">
        <Tabs defaultValue="notes" className="flex flex-col h-full">
          <div className="border-b px-4 pt-3">
            <TabsList>
              <TabsTrigger value="notes">
                <FileText className="w-3 h-3 mr-1" />
                SOAP Notes
                {noteStatus === "final" && <CheckCircle className="w-3 h-3 ml-1 text-green-500" />}
              </TabsTrigger>
              <TabsTrigger value="prescription">
                <Pill className="w-3 h-3 mr-1" />
                Prescription
                {signedRx && <CheckCircle className="w-3 h-3 ml-1 text-green-500" />}
              </TabsTrigger>
            </TabsList>
          </div>

          {/* SOAP Notes Tab */}
          <TabsContent value="notes" className="flex-1 overflow-y-auto p-4 space-y-4 mt-0">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <h3 className="font-semibold">SOAP Notes</h3>
                <Badge className={noteStatus === "final" ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"}>
                  {noteStatus === "final" ? "Final" : "Draft — AI Generated"}
                </Badge>
              </div>
              <Button
                size="sm"
                onClick={handleGenerateSOAP}
                disabled={generatingNote || generatedCount >= 2}
              >
                {generatingNote ? <Loader2 className="animate-spin w-3 h-3 mr-1" /> : <Sparkles className="w-3 h-3 mr-1" />}
                {generatedCount === 0 ? "Generate Notes" : "Regenerate"}
              </Button>
            </div>

            {generatedCount > 0 && noteStatus === "draft" && (
              <div className="flex items-start gap-2 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm">
                <AlertTriangle className="w-4 h-4 text-yellow-600 shrink-0 mt-0.5" />
                <p className="text-yellow-800">AI-generated draft. Review and edit before finalizing.</p>
              </div>
            )}

            {[
              { key: "subjective", label: "Subjective (Patient History & Symptoms)" },
              { key: "objective", label: "Objective (Findings & Observations)" },
              { key: "assessment", label: "Assessment (Diagnosis)" },
              { key: "plan", label: "Plan (Treatment & Follow-up)" },
              { key: "investigations", label: "Investigations / Tests" },
              { key: "follow_up_notes", label: "Follow-up Instructions" },
            ].map(({ key, label }) => (
              <div key={key}>
                <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</Label>
                <Textarea
                  value={soapNote[key as keyof typeof soapNote]}
                  onChange={(e) => setSoapNote((p) => ({ ...p, [key]: e.target.value }))}
                  className="mt-1 text-sm"
                  rows={3}
                  disabled={noteStatus === "final"}
                />
              </div>
            ))}

            {noteStatus !== "final" && (
              <div className="flex gap-2 sticky bottom-0 bg-white py-3 border-t">
                <Button variant="outline" onClick={handleSaveSOAP} className="flex-1">
                  Save Draft
                </Button>
                <Button onClick={handleFinalizeSOAP} className="flex-1">
                  <CheckCircle className="w-4 h-4 mr-1" />
                  Finalize Notes
                </Button>
              </div>
            )}
          </TabsContent>

          {/* Prescription Tab */}
          <TabsContent value="prescription" className="flex-1 overflow-y-auto p-4 space-y-4 mt-0">
            {signedRx ? (
              <div className="text-center py-8 space-y-4">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                  <CheckCircle className="w-8 h-8 text-green-600" />
                </div>
                <h3 className="font-semibold">Prescription Signed</h3>
                <p className="text-sm text-muted-foreground">Patient has been notified.</p>
                {signedRx.pdf_path && (
                  <a
                    href={`${API_BASE_URL}/api/v1/prescriptions/download/${signedRx.pdf_token}`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <Button variant="outline" size="sm">Download PDF</Button>
                  </a>
                )}
              </div>
            ) : (
              <>
                <div>
                  <Label>Diagnosis</Label>
                  <Input
                    placeholder="Enter diagnosis..."
                    value={diagnosis}
                    onChange={(e) => setDiagnosis(e.target.value)}
                    className="mt-1"
                  />
                </div>

                {/* Drug search */}
                <div>
                  <Label>Add Medication</Label>
                  <div className="relative mt-1">
                    <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-muted-foreground" />
                    <Input
                      placeholder="Search drugs..."
                      value={drugSearch}
                      onChange={(e) => handleDrugSearch(e.target.value)}
                      className="pl-8"
                    />
                    {searchingDrugs && (
                      <Loader2 className="absolute right-2.5 top-2.5 w-4 h-4 animate-spin text-muted-foreground" />
                    )}
                  </div>
                  {drugResults.length > 0 && (
                    <div className="border rounded-lg mt-1 bg-white shadow-lg max-h-40 overflow-y-auto z-10">
                      {drugResults.map((drug) => (
                        <button
                          key={drug.id}
                          onClick={() => addMedication(drug)}
                          className="w-full text-left px-3 py-2 text-sm hover:bg-muted border-b last:border-0"
                        >
                          <span className="font-medium">{drug.name}</span>
                          {drug.generic_name && drug.generic_name !== drug.name && (
                            <span className="text-muted-foreground ml-1 text-xs">({drug.generic_name})</span>
                          )}
                          {drug.drug_class && (
                            <span className="text-muted-foreground ml-2 text-xs">— {drug.drug_class}</span>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Interaction warnings */}
                {interactionWarnings.length > 0 && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3 space-y-1">
                    <p className="text-sm font-semibold text-red-700 flex items-center gap-1">
                      <AlertTriangle className="w-4 h-4" />
                      Drug Interaction Warnings
                    </p>
                    {interactionWarnings.map((w, i) => (
                      <p key={i} className="text-xs text-red-600">
                        {w.type === "allergy_alert" ? "⚠ Allergy: " : "⚠ "}
                        {w.description}
                      </p>
                    ))}
                  </div>
                )}

                {/* Medication list */}
                {medications.length > 0 && (
                  <div className="space-y-3">
                    {medications.map((med, i) => (
                      <Card key={i} className="border-l-4 border-l-primary">
                        <CardContent className="p-3 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="font-medium text-sm">{med.drug_name}</span>
                            <button onClick={() => removeMedication(i)} className="text-muted-foreground hover:text-destructive">
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                          <div className="grid grid-cols-2 gap-2">
                            <div>
                              <Label className="text-xs">Strength</Label>
                              <Input
                                value={med.strength}
                                onChange={(e) => updateMedication(i, "strength", e.target.value)}
                                placeholder="e.g. 500mg"
                                className="h-8 text-xs mt-0.5"
                              />
                            </div>
                            <div>
                              <Label className="text-xs">Frequency</Label>
                              <Input
                                value={med.frequency}
                                onChange={(e) => updateMedication(i, "frequency", e.target.value)}
                                placeholder="e.g. Twice daily"
                                className="h-8 text-xs mt-0.5"
                              />
                            </div>
                            <div>
                              <Label className="text-xs">Duration</Label>
                              <Input
                                value={med.duration}
                                onChange={(e) => updateMedication(i, "duration", e.target.value)}
                                placeholder="e.g. 7 days"
                                className="h-8 text-xs mt-0.5"
                              />
                            </div>
                            <div>
                              <Label className="text-xs">Form</Label>
                              <Input
                                value={med.dosage_form}
                                onChange={(e) => updateMedication(i, "dosage_form", e.target.value)}
                                placeholder="tablet"
                                className="h-8 text-xs mt-0.5"
                              />
                            </div>
                          </div>
                          <div>
                            <Label className="text-xs">Instructions</Label>
                            <Input
                              value={med.instructions}
                              onChange={(e) => updateMedication(i, "instructions", e.target.value)}
                              placeholder="e.g. After meals"
                              className="h-8 text-xs mt-0.5"
                            />
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}

                {medications.length >= 2 && (
                  <Button variant="outline" size="sm" onClick={handleCheckInteractions} className="w-full">
                    <AlertTriangle className="w-3 h-3 mr-1" />
                    Check Drug Interactions
                  </Button>
                )}

                <div className="sticky bottom-0 bg-white pt-3 border-t">
                  <Button
                    className="w-full"
                    onClick={handleSignPrescription}
                    disabled={signingRx || medications.length === 0}
                  >
                    {signingRx ? <Loader2 className="animate-spin mr-2 w-4 h-4" /> : <Send className="w-4 h-4 mr-2" />}
                    Sign & Send Prescription
                  </Button>
                </div>
              </>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
