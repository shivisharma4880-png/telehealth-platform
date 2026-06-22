"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Shield, Loader2, Search } from "lucide-react";
import { formatDateTime } from "@/lib/utils";

const EVENT_COLORS: Record<string, string> = {
  user_login: "bg-blue-100 text-blue-700",
  appointment_booked: "bg-green-100 text-green-700",
  soap_note_generated: "bg-purple-100 text-purple-700",
  soap_note_edited: "bg-yellow-100 text-yellow-700",
  soap_note_finalized: "bg-green-100 text-green-700",
  prescription_created: "bg-sky-100 text-sky-700",
  prescription_signed: "bg-indigo-100 text-indigo-700",
  consultation_started: "bg-amber-100 text-amber-700",
  consultation_ended: "bg-gray-100 text-gray-700",
};

export default function AdminAuditPage() {
  const { accessToken } = useAuthStore();
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    if (accessToken) {
      const params = filter ? `?event_type=${filter}` : "";
      api.get<any[]>(`/admin/audit-logs${params}`, accessToken)
        .then((data) => setEvents(Array.isArray(data) ? data : []))
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [accessToken, filter]);

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Shield className="w-6 h-6 text-primary" />
          Audit Logs
        </h1>
        <p className="text-muted-foreground">Append-only record of all key system events for compliance</p>
      </div>

      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Filter by event type (e.g. user_login, prescription_signed)..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="pl-9"
          />
        </div>
        <Button variant="outline" onClick={() => setFilter("")}>Clear</Button>
      </div>

      <div className="text-xs text-muted-foreground flex items-center gap-2">
        <Shield className="w-3 h-3" />
        These logs are append-only and cannot be modified or deleted.
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48"><Loader2 className="animate-spin" /></div>
      ) : (
        <Card>
          <CardContent className="p-0">
            {events.length === 0 ? (
              <p className="text-center text-muted-foreground py-8 text-sm">No audit events found.</p>
            ) : (
              <div className="divide-y">
                {events.map((event) => (
                  <div key={event.id} className="flex items-start gap-4 px-4 py-3 hover:bg-muted/30">
                    <Badge className={`shrink-0 ${EVENT_COLORS[event.event_type] || "bg-gray-100 text-gray-700"}`}>
                      {event.event_type.replace(/_/g, " ")}
                    </Badge>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm">{event.description || `${event.resource_type} ${event.resource_id}`}</p>
                      <div className="flex items-center gap-3 mt-0.5 text-xs text-muted-foreground">
                        <span>{event.user_id ? `User: ${event.user_id.slice(0, 8)}…` : "System"}</span>
                        {event.ip_address && <span>IP: {event.ip_address}</span>}
                      </div>
                    </div>
                    <span className="text-xs text-muted-foreground shrink-0">
                      {formatDateTime(event.created_at)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
