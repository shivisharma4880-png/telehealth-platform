"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/toaster";
import { Loader2, Save, Building } from "lucide-react";

export default function AdminSettingsPage() {
  const { accessToken } = useAuthStore();
  const { toast } = useToast();
  const [org, setOrg] = useState<any>(null);
  const [form, setForm] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (accessToken) {
      api.get<any>("/admin/organization", accessToken)
        .then((data) => {
          setOrg(data);
          setForm(data);
        })
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [accessToken]);

  async function handleSave() {
    setSaving(true);
    try {
      await api.put("/admin/organization", form, accessToken);
      toast({ title: "Settings saved!" });
    } catch (err: any) {
      toast({ title: "Error", description: err.message, variant: "destructive" });
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center h-48"><Loader2 className="animate-spin" /></div>;
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Building className="w-6 h-6 text-primary" />
          Clinic Settings
        </h1>
        <p className="text-muted-foreground">Configure your clinic profile and policies</p>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">Clinic Information</CardTitle></CardHeader>
        <CardContent className="grid gap-4">
          {[
            { key: "name", label: "Clinic Name" },
            { key: "address", label: "Address" },
            { key: "phone", label: "Phone Number" },
            { key: "email", label: "Email" },
            { key: "registration_number", label: "Registration Number" },
            { key: "branding_color", label: "Brand Color (hex)", placeholder: "#0ea5e9" },
            { key: "cancellation_policy_hours", label: "Cancellation Policy (hours notice)", type: "number" },
          ].map(({ key, label, type, placeholder }) => (
            <div key={key}>
              <Label>{label}</Label>
              <Input
                type={type || "text"}
                value={form[key] || ""}
                placeholder={placeholder}
                onChange={(e) => setForm((p: any) => ({ ...p, [key]: type === "number" ? Number(e.target.value) : e.target.value }))}
                className="mt-1"
              />
            </div>
          ))}
        </CardContent>
      </Card>

      <div className="flex items-center gap-2 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
        <span>Prescription PDFs will use your clinic name and branding color automatically.</span>
      </div>

      <Button onClick={handleSave} disabled={saving}>
        {saving ? <Loader2 className="animate-spin mr-2 w-4 h-4" /> : <Save className="w-4 h-4 mr-2" />}
        Save Settings
      </Button>
    </div>
  );
}
