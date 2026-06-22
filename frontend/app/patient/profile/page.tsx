"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/toaster";
import { Loader2, User, Save } from "lucide-react";

export default function PatientProfilePage() {
  const { accessToken } = useAuthStore();
  const { toast } = useToast();
  const [profile, setProfile] = useState<any>(null);
  const [form, setForm] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (accessToken) {
      api.get<any>("/patients/me", accessToken)
        .then((data) => {
          setProfile(data);
          setForm(data);
        })
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [accessToken]);

  async function handleSave() {
    setSaving(true);
    try {
      await api.put("/patients/me", form, accessToken);
      toast({ title: "Profile updated!" });
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
    <div className="space-y-6 max-w-lg">
      <h1 className="text-2xl font-bold">My Profile</h1>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-14 h-14 rounded-full bg-gradient-to-br from-sky-400 to-blue-600 flex items-center justify-center text-white text-xl font-bold">
              {profile?.first_name?.[0]}{profile?.last_name?.[0]}
            </div>
            <div>
              <CardTitle>{profile?.first_name} {profile?.last_name}</CardTitle>
              <p className="text-sm text-muted-foreground">Patient Profile</p>
            </div>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4">
          {[
            { key: "first_name", label: "First Name" },
            { key: "last_name", label: "Last Name" },
            { key: "date_of_birth", label: "Date of Birth", type: "date" },
            { key: "abha_id", label: "ABHA ID (optional)" },
          ].map(({ key, label, type }) => (
            <div key={key}>
              <Label>{label}</Label>
              <Input
                type={type || "text"}
                value={form[key] || ""}
                onChange={(e) => setForm((p: any) => ({ ...p, [key]: e.target.value }))}
                className="mt-1"
              />
            </div>
          ))}
          <div>
            <Label>Gender</Label>
            <select
              value={form.gender || ""}
              onChange={(e) => setForm((p: any) => ({ ...p, gender: e.target.value }))}
              className="mt-1 w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="">Prefer not to say</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div>
            <Label>Known Allergies (comma-separated)</Label>
            <Input
              value={(form.allergies || []).join(", ")}
              onChange={(e) => setForm((p: any) => ({
                ...p,
                allergies: e.target.value.split(",").map((s: string) => s.trim()).filter(Boolean),
              }))}
              placeholder="e.g. penicillin, aspirin"
              className="mt-1"
            />
          </div>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? <Loader2 className="animate-spin mr-2 w-4 h-4" /> : <Save className="w-4 h-4 mr-2" />}
            Save Profile
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
