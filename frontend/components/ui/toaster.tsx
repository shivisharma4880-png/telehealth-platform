"use client";
import { useEffect } from "react";
import { useToastStore } from "@/lib/store";

export function Toaster() {
  const { toasts, removeToast } = useToastStore();
  const list = Array.isArray(toasts) ? toasts : [];

  useEffect(() => {
    list.forEach((toast) => {
      const timer = setTimeout(() => removeToast(toast.id), 5000);
      return () => clearTimeout(timer);
    });
  }, [list, removeToast]);

  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2 max-w-sm">
      {list.map((toast) => (
        <div
          key={toast.id}
          className={`rounded-lg border p-4 shadow-lg animate-in slide-in-from-right ${
            toast.variant === "destructive"
              ? "bg-destructive text-destructive-foreground border-destructive"
              : "bg-card text-card-foreground border-border"
          }`}
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="font-medium text-sm">{toast.title}</p>
              {toast.description && <p className="text-sm opacity-80 mt-1">{toast.description}</p>}
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              className="text-current opacity-60 hover:opacity-100 text-lg leading-none"
            >
              ×
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

export function useToast() {
  const { addToast } = useToastStore();
  return {
    toast: (options: { title: string; description?: string; variant?: "default" | "destructive" }) =>
      addToast(options),
  };
}
