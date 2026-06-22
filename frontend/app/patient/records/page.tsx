"use client";
import { useEffect, useState } from "react";
import { api, API_BASE_URL } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatDateTime, getStatusColor } from "@/lib/utils";
import { Download, Pill, Loader2 } from "lucide-react";

export default function PatientRecordsPage() {
  const { accessToken } = useAuthStore();
  const [prescriptions, setPrescriptions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (accessToken) {
      api.get<any[]>("/prescriptions/my", accessToken)
        .then((data) => setPrescriptions(Array.isArray(data) ? data : []))
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
        <h1 className="text-2xl font-bold">My Records</h1>
        <p className="text-muted-foreground">Your visit summaries and prescriptions</p>
      </div>

      <Tabs defaultValue="prescriptions">
        <TabsList>
          <TabsTrigger value="prescriptions">Prescriptions</TabsTrigger>
        </TabsList>

        <TabsContent value="prescriptions" className="mt-4">
          {prescriptions.length === 0 ? (
            <Card>
              <CardContent className="p-12 text-center">
                <Pill className="w-12 h-12 mx-auto text-muted-foreground mb-3" />
                <p className="text-muted-foreground">No prescriptions yet</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {prescriptions.map((rx) => (
                <Card key={rx.id}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">
                        {rx.voice_consult_session_id
                          ? "AI voice consultation"
                          : `Prescription #${rx.id.slice(0, 8).toUpperCase()}`}
                      </CardTitle>
                      <Badge className={getStatusColor(rx.status)}>
                        {rx.status === "ai_consult_record" ? "AI consult record" : rx.status}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">{formatDateTime(rx.created_at)}</p>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {rx.diagnosis && (
                      <p className="text-sm"><strong>Diagnosis / summary:</strong> {rx.diagnosis}</p>
                    )}
                    {rx.notes && (
                      <div className="text-sm text-muted-foreground whitespace-pre-wrap border-l-2 border-muted pl-3">
                        {rx.notes}
                      </div>
                    )}
                    {Array.isArray(rx.medication_requests) && rx.medication_requests.length > 0 && (
                      <div>
                        <p className="text-sm font-medium mb-1">Medications:</p>
                        <ul className="space-y-1">
                          {rx.medication_requests.map((med: any) => (
                            <li key={med.id} className="text-sm text-muted-foreground flex items-center gap-2">
                              <Pill className="w-3 h-3 shrink-0" />
                              <span>
                                <strong>{med.drug_name}</strong>
                                {med.strength && ` ${med.strength}`}
                                {` — ${med.frequency}`}
                                {med.duration && `, ${med.duration}`}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {rx.pdf_token && rx.pdf_path && (
                      <a
                        href={`${API_BASE_URL}/api/v1/prescriptions/download/${rx.pdf_token}`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <Button size="sm" variant="outline">
                          <Download className="w-3 h-3 mr-1" />
                          Download PDF
                        </Button>
                      </a>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
