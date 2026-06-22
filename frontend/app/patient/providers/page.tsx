"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { SPECIALTY_LABELS, formatCurrency } from "@/lib/utils";
import { Search, Star, Clock, Languages, IndianRupee, Calendar } from "lucide-react";

const SPECIALTIES = [
  { value: "", label: "All" },
  { value: "general_practice", label: "General Practice" },
  { value: "dermatology", label: "Dermatology" },
  { value: "mental_health", label: "Mental Health" },
  { value: "pediatrics", label: "Pediatrics" },
];

export default function ProvidersPage() {
  const { accessToken } = useAuthStore();
  const router = useRouter();
  const [practitioners, setPractitioners] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedSpecialty, setSelectedSpecialty] = useState("");

  useEffect(() => {
    const params = new URLSearchParams();
    if (selectedSpecialty) params.set("specialty", selectedSpecialty);

    api.get<any[]>(`/practitioners/?${params}`, accessToken)
      .then((data) => setPractitioners(Array.isArray(data) ? data : []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [selectedSpecialty, accessToken]);

  const filtered = practitioners.filter((p) => {
    const name = `${p.first_name} ${p.last_name}`.toLowerCase();
    return name.includes(searchTerm.toLowerCase());
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Find a Doctor</h1>
        <p className="text-muted-foreground">Book a teleconsultation with verified doctors</p>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-3 w-4 h-4 text-muted-foreground" />
        <Input
          placeholder="Search by doctor name..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Specialty filter */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {SPECIALTIES.map((s) => (
          <button
            key={s.value}
            onClick={() => setSelectedSpecialty(s.value)}
            className={`px-4 py-2 rounded-full text-sm whitespace-nowrap transition-colors ${
              selectedSpecialty === s.value
                ? "bg-primary text-white"
                : "bg-white border hover:bg-gray-50"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Results */}
      {loading ? (
        <div className="grid gap-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-4 h-32 bg-gray-100 rounded-lg" />
            </Card>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            No doctors found for your search.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {filtered.map((doc) => (
            <Card key={doc.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-start gap-4">
                  {/* Avatar */}
                  <div className="w-16 h-16 rounded-full bg-gradient-to-br from-sky-400 to-blue-600 flex items-center justify-center text-white text-xl font-bold shrink-0">
                    {doc.first_name[0]}{doc.last_name[0]}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h3 className="font-semibold">Dr. {doc.first_name} {doc.last_name}</h3>
                        <Badge variant="secondary" className="text-xs mt-1">
                          {SPECIALTY_LABELS[doc.specialty] || doc.specialty}
                        </Badge>
                      </div>
                      <div className="text-right shrink-0">
                        <p className="font-semibold text-primary">
                          {doc.consultation_fee > 0 ? formatCurrency(doc.consultation_fee) : "Free"}
                        </p>
                        <p className="text-xs text-muted-foreground">per consult</p>
                      </div>
                    </div>

                    {doc.bio && (
                      <p className="text-sm text-muted-foreground mt-2 line-clamp-2">{doc.bio}</p>
                    )}

                    <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {doc.years_of_experience}y exp
                      </span>
                      <span className="flex items-center gap-1">
                        <Languages className="w-3 h-3" />
                        {(doc.languages || []).join(", ").toUpperCase()}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {doc.slot_duration_minutes}m slots
                      </span>
                    </div>

                    <Button
                      className="mt-3 w-full sm:w-auto"
                      size="sm"
                      onClick={() => router.push(`/patient/book/${doc.id}`)}
                    >
                      <Calendar className="w-3 h-3 mr-1" />
                      Book Appointment
                    </Button>
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
