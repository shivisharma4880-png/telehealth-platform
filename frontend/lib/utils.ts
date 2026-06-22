import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { format, formatDistanceToNow } from "date-fns";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDateTime(dt: string | Date): string {
  const d = typeof dt === "string" ? new Date(dt) : dt;
  return format(d, "dd MMM yyyy, hh:mm a");
}

export function formatDate(dt: string | Date): string {
  const d = typeof dt === "string" ? new Date(dt) : dt;
  return format(d, "dd MMM yyyy");
}

export function formatTime(dt: string | Date): string {
  const d = typeof dt === "string" ? new Date(dt) : dt;
  return format(d, "hh:mm a");
}

export function timeFromNow(dt: string | Date): string {
  const d = typeof dt === "string" ? new Date(dt) : dt;
  return formatDistanceToNow(d, { addSuffix: true });
}

export function formatCurrency(amount: number, currency = "INR"): string {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency }).format(amount);
}

export function getStatusColor(status: string): string {
  const map: Record<string, string> = {
    booked: "bg-blue-100 text-blue-700",
    confirmed: "bg-sky-100 text-sky-700",
    in_progress: "bg-amber-100 text-amber-700",
    completed: "bg-green-100 text-green-700",
    no_show: "bg-orange-100 text-orange-700",
    cancelled: "bg-red-100 text-red-700",
    rescheduled: "bg-purple-100 text-purple-700",
    pending: "bg-yellow-100 text-yellow-700",
    paid: "bg-green-100 text-green-700",
    refunded: "bg-gray-100 text-gray-700",
    failed: "bg-red-100 text-red-700",
    draft: "bg-yellow-100 text-yellow-700",
    final: "bg-green-100 text-green-700",
    signed: "bg-green-100 text-green-700",
    ai_consult_record: "bg-violet-100 text-violet-800",
  };
  return map[status] || "bg-gray-100 text-gray-700";
}

export const SPECIALTY_LABELS: Record<string, string> = {
  general_practice: "General Practice",
  dermatology: "Dermatology",
  mental_health: "Mental Health",
  pediatrics: "Pediatrics",
  cardiology: "Cardiology",
  orthopedics: "Orthopedics",
  other: "Other",
};
