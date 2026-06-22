"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Phone, PhoneOff, Mic, Loader2, Bot, ClipboardList, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuthStore } from "@/lib/store";
import { API_BASE_URL } from "@/lib/api";

const MAX_TURNS = 3;
const VOICE_DRAFT_KEY = "voiceConsultDraft";

type LogLine = { speaker: "you" | "doctor"; text: string };

type SessionCreateResponse = {
  session_id: string;
  welcome_text: string;
  welcome_audio_base64: string;
  mime_type: string;
};

type TurnResponse = {
  transcript: string;
  reply_text: string;
  reply_audio_base64: string;
  mime_type: string;
  turn: number;
  session_complete: boolean;
  final_result?: Record<string, string> | null;
  summary_pdf_token?: string | null;
};

function pickRecorderMime(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) return "audio/webm;codecs=opus";
  if (MediaRecorder.isTypeSupported("audio/webm")) return "audio/webm";
  return undefined;
}

function playBase64Audio(base64: string, mime: string): Promise<void> {
  return new Promise((resolve, reject) => {
    try {
      const binary = atob(base64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
      }
      const blob = new Blob([bytes], { type: mime });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.onended = () => {
        URL.revokeObjectURL(url);
        resolve();
      };
      audio.onerror = () => {
        URL.revokeObjectURL(url);
        reject(new Error("Audio playback failed"));
      };
      void audio.play().catch(reject);
    } catch (e) {
      reject(e instanceof Error ? e : new Error("Invalid audio data"));
    }
  });
}

function clearVoiceDraft() {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem(VOICE_DRAFT_KEY);
  } catch {
    /* ignore */
  }
}

/** Secure context only: HTTPS, localhost, or 127.0.0.1. Plain http:// on a LAN/VM IP leaves `mediaDevices` undefined. */
function getUserMicStream(): Promise<MediaStream> {
  const md = typeof navigator !== "undefined" ? navigator.mediaDevices : undefined;
  if (!md?.getUserMedia) {
    return Promise.reject(
      new Error(
        "Microphone needs a secure page (HTTPS) or http://localhost. Plain HTTP on a remote host cannot access the mic.",
      ),
    );
  }
  return md.getUserMedia({ audio: true });
}

export default function PatientAudioConsultPage() {
  const router = useRouter();
  const { accessToken } = useAuthStore();
  const [callStarted, setCallStarted] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [micError, setMicError] = useState<string | null>(null);
  const [phase, setPhase] = useState<"idle" | "recording" | "sending" | "starting">("idle");
  const [log, setLog] = useState<LogLine[]>([]);
  const [currentTurn, setCurrentTurn] = useState(0);
  const [sessionComplete, setSessionComplete] = useState(false);
  const [finalResult, setFinalResult] = useState<Record<string, string> | null>(null);
  const [summaryPdfToken, setSummaryPdfToken] = useState<string | null>(null);

  const [appointmentIdFromUrl, setAppointmentIdFromUrl] = useState<string | null>(null);
  const [draftRestored, setDraftRestored] = useState(false);

  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const appt = params.get("appointmentId");
    setAppointmentIdFromUrl(appt);

    const raw = sessionStorage.getItem(VOICE_DRAFT_KEY);
    if (!raw) return;
    try {
      const d = JSON.parse(raw) as {
        sessionId?: string;
        log?: LogLine[];
        currentTurn?: number;
        sessionComplete?: boolean;
        appointmentId?: string | null;
      };
      if (!d.sessionId || d.sessionComplete) return;
      if (appt && d.appointmentId && d.appointmentId !== appt) {
        clearVoiceDraft();
        return;
      }
      setSessionId(d.sessionId);
      setLog(Array.isArray(d.log) ? d.log : []);
      setCurrentTurn(typeof d.currentTurn === "number" ? d.currentTurn : 0);
      setCallStarted(true);
      setSessionComplete(false);
      setDraftRestored(true);
    } catch {
      clearVoiceDraft();
    }
  }, []);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [log, phase]);

  useEffect(() => {
    if (!draftRestored || !callStarted || !sessionId || sessionComplete || streamRef.current) return;
    let cancelled = false;
    (async () => {
      try {
        const stream = await getUserMicStream();
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
      } catch (e) {
        if (!cancelled) {
          const msg =
            e instanceof Error
              ? e.message
              : "Microphone is required to continue after refresh. Tap End call and start again.";
          setMicError(msg);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [draftRestored, callStarted, sessionId, sessionComplete]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!sessionId || sessionComplete) {
      if (sessionComplete) clearVoiceDraft();
      return;
    }
    try {
      sessionStorage.setItem(
        VOICE_DRAFT_KEY,
        JSON.stringify({
          sessionId,
          log,
          currentTurn,
          sessionComplete: false,
          appointmentId: appointmentIdFromUrl,
        }),
      );
    } catch {
      /* ignore quota */
    }
  }, [sessionId, log, currentTurn, sessionComplete, appointmentIdFromUrl]);

  const autoLockKey = useCallback(() => {
    if (typeof window === "undefined") return "vcAuto_solo";
    const ap = new URLSearchParams(window.location.search).get("appointmentId");
    return "vcAuto_" + (ap || "solo");
  }, []);

  const startCall = async () => {
    clearVoiceDraft();
    setMicError(null);
    if (!accessToken) {
      router.push("/login");
      return;
    }
    setPhase("starting");
    try {
      const stream = await getUserMicStream();
      streamRef.current = stream;

      const q = appointmentIdFromUrl
        ? `?appointment_id=${encodeURIComponent(appointmentIdFromUrl)}`
        : "";
      const res = await fetch(`${API_BASE_URL}/api/v1/audio-consult/sessions${q}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const detail = err.detail;
        const msg = typeof detail === "string" ? detail : `HTTP ${res.status}`;
        throw new Error(msg);
      }
      const data = (await res.json()) as SessionCreateResponse;
      setSessionId(data.session_id);
      setCallStarted(true);
      setSessionComplete(false);
      setFinalResult(null);
      setSummaryPdfToken(null);
      setCurrentTurn(0);
      setLog([{ speaker: "doctor", text: data.welcome_text }]);

      await playBase64Audio(data.welcome_audio_base64, data.mime_type);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Could not start voice session.";
      setMicError(msg);
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      setCallStarted(false);
      setSessionId(null);
    } finally {
      setPhase("idle");
    }
  };

  const endCall = () => {
    try {
      sessionStorage.removeItem(autoLockKey());
    } catch {
      /* ignore */
    }
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    recorderRef.current = null;
    setCallStarted(false);
    setSessionId(null);
    setPhase("idle");
    setLog([]);
    setCurrentTurn(0);
    setSessionComplete(false);
    setFinalResult(null);
    setSummaryPdfToken(null);
    setDraftRestored(false);
    clearVoiceDraft();
  };

  const beginRecording = useCallback(() => {
    const stream = streamRef.current;
    if (!stream || phase === "sending" || sessionComplete || !sessionId) return;
    chunksRef.current = [];
    const mime = pickRecorderMime();
    const rec = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
    rec.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };
    rec.start(200);
    recorderRef.current = rec;
    setPhase("recording");
  }, [phase, sessionComplete, sessionId]);

  const finishRecordingAndSend = useCallback(async () => {
    const rec = recorderRef.current;
    if (!rec || rec.state === "inactive") {
      setPhase("idle");
      return;
    }

    await new Promise<void>((resolve) => {
      rec.onstop = () => resolve();
      rec.stop();
    });
    recorderRef.current = null;

    const mime = pickRecorderMime() || "audio/webm";
    const blob = new Blob(chunksRef.current, { type: mime });
    chunksRef.current = [];

    if (blob.size < 800) {
      setPhase("idle");
      setLog((l) => [
        ...l,
        {
          speaker: "doctor",
          text: "That clip was very short — hold the button a bit longer while you speak.",
        },
      ]);
      return;
    }

    if (!accessToken || !sessionId) {
      router.push("/login");
      return;
    }

    setPhase("sending");
    const fd = new FormData();
    fd.append("audio", blob, "turn.webm");

    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/audio-consult/sessions/${sessionId}/turn`, {
        method: "POST",
        headers: { Authorization: `Bearer ${accessToken}` },
        body: fd,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const detail = err.detail;
        const msg = typeof detail === "string" ? detail : `HTTP ${res.status}`;
        throw new Error(msg);
      }
      const data = (await res.json()) as TurnResponse;

      if (data.transcript) {
        setLog((l) => [...l, { speaker: "you", text: data.transcript }]);
      }
      setLog((l) => [...l, { speaker: "doctor", text: data.reply_text }]);

      setCurrentTurn(data.turn);
      if (data.session_complete) {
        setSessionComplete(true);
        if (data.final_result && typeof data.final_result === "object") {
          setFinalResult(data.final_result as Record<string, string>);
        }
        if (data.summary_pdf_token) {
          setSummaryPdfToken(data.summary_pdf_token);
        }
        try {
          sessionStorage.removeItem(autoLockKey());
        } catch {
          /* ignore */
        }
      }

      await playBase64Audio(data.reply_audio_base64, data.mime_type);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Something went wrong";
      setLog((l) => [...l, { speaker: "doctor", text: msg }]);
    } finally {
      setPhase("idle");
    }
  }, [accessToken, router, sessionId, autoLockKey]);

  const micBusy = phase === "sending" || phase === "starting";
  const canRecord = callStarted && sessionId && !sessionComplete && !micBusy;

  return (
    <div className="max-w-lg mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">AI doctor — audio visit</h1>
        <Button variant="ghost" size="sm" asChild>
          <Link href="/patient/home">Back</Link>
        </Button>
      </div>

      {appointmentIdFromUrl && (
        <Card className="border-sky-200 bg-sky-50/80">
          <CardContent className="p-3 text-sm text-sky-950">
            This session is linked to your <strong>booked appointment</strong>. After you finish all speaking turns,
            a consult summary is saved under <strong>My Records → Prescriptions</strong> for you to share with a
            clinician.
          </CardContent>
        </Card>
      )}

      <Card className="border-emerald-200 bg-emerald-50/50">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2 text-emerald-900">
            <Bot className="w-5 h-5" />
            AI voice session
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-emerald-900/80 space-y-2">
          <p>
            This <strong>voice session</strong> uses Groq for speech-to-text, language models, and text-to-speech. The
            AI is <strong>not a licensed physician</strong>. For emergencies, use real emergency services — not this
            screen.
          </p>
          <p className="text-xs">
            After a short welcome, you will have <strong>{MAX_TURNS} speaking turns</strong>. Turns 1–2 are follow-up
            questions; turn {MAX_TURNS} is a closing summary. When the session completes, a consult record (including
            draft notes for a clinician) is saved under <strong>My Records → Prescriptions</strong>.
          </p>
        </CardContent>
      </Card>

      {micError && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-4 text-sm text-red-800">{micError}</CardContent>
        </Card>
      )}

      {sessionComplete && (
        <Card className="border-violet-200 bg-violet-50/80">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2 text-violet-900">
              <ClipboardList className="w-5 h-5" />
              Session summary (draft — confirm with a clinician)
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-violet-950/90 space-y-3">
            {finalResult?.summary ? (
              <div>
                <p className="font-medium text-xs uppercase text-violet-700">Summary</p>
                <p className="mt-1 whitespace-pre-wrap">{finalResult.summary}</p>
              </div>
            ) : null}
            {finalResult?.assessment_discussion ? (
              <div>
                <p className="font-medium text-xs uppercase text-violet-700">Discussion</p>
                <p className="mt-1 whitespace-pre-wrap">{finalResult.assessment_discussion}</p>
              </div>
            ) : null}
            {finalResult?.recommendations ? (
              <div>
                <p className="font-medium text-xs uppercase text-violet-700">Recommendations</p>
                <p className="mt-1 whitespace-pre-wrap">{finalResult.recommendations}</p>
              </div>
            ) : null}
            {finalResult?.prescription_draft ? (
              <div>
                <p className="font-medium text-xs uppercase text-violet-700">Prescription discussion draft</p>
                <p className="mt-1 whitespace-pre-wrap">{finalResult.prescription_draft}</p>
              </div>
            ) : null}
            <p className="text-xs text-violet-800">
              A copy of this consult is saved under <strong>My Records → Prescriptions</strong> for your records.
            </p>
            {summaryPdfToken ? (
              <Button className="w-full" asChild variant="default">
                <a
                  href={`${API_BASE_URL}/api/v1/prescriptions/download/${summaryPdfToken}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Download visit summary (PDF)
                </a>
              </Button>
            ) : null}
            <Button className="w-full" asChild variant="secondary">
              <Link href="/patient/records">Open My Records (Prescriptions)</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {!callStarted ? (
        <Card>
          <CardContent className="p-8 flex flex-col items-center text-center gap-4">
            <div className="w-20 h-20 rounded-full bg-emerald-100 flex items-center justify-center">
              <Phone className="w-10 h-10 text-emerald-700" />
            </div>
            <p className="text-muted-foreground text-sm">
              Tap <strong>Start audio call</strong> to allow the microphone (required by your browser). The server will
              play a welcome message using Groq voice synthesis.
            </p>
            <Button
              size="lg"
              className="rounded-full px-8 bg-emerald-600 hover:bg-emerald-700"
              onClick={() => {
                try {
                  sessionStorage.removeItem(autoLockKey());
                } catch {
                  /* ignore */
                }
                void startCall();
              }}
              disabled={phase === "starting"}
            >
              {phase === "starting" ? (
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              ) : (
                <Phone className="w-5 h-5 mr-2" />
              )}
              Start audio call
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <CardContent className="p-0">
            <div className="bg-gradient-to-b from-emerald-900 to-slate-900 text-white p-4 text-center">
              <p className="text-xs uppercase tracking-widest text-emerald-200/90">Groq voice line</p>
              <p className="text-lg font-semibold mt-1">Dr. Arjun (AI)</p>
              <p className="text-xs text-emerald-100/80 mt-1">
                {sessionComplete
                  ? "Session complete"
                  : phase === "recording"
                    ? "Listening…"
                    : micBusy
                      ? "Working…"
                      : `Speaking turns completed: ${currentTurn} / ${MAX_TURNS}`}
              </p>
            </div>

            <div className="h-56 overflow-y-auto p-3 space-y-3 bg-slate-50 border-b">
              {log.map((line, i) => (
                <div
                  key={i}
                  className={`text-sm rounded-lg px-3 py-2 max-w-[92%] ${
                    line.speaker === "you"
                      ? "bg-sky-100 text-sky-950 ml-auto"
                      : "bg-white border shadow-sm text-slate-800 mr-auto"
                  }`}
                >
                  <span className="text-[10px] font-semibold uppercase text-muted-foreground">
                    {line.speaker === "you" ? "You" : "Dr. Arjun"}
                  </span>
                  <p className="mt-1 whitespace-pre-wrap leading-snug">{line.text}</p>
                </div>
              ))}
              <div ref={logEndRef} />
            </div>

            <div className="p-4 flex flex-col items-center gap-3 bg-white">
              <button
                type="button"
                disabled={!canRecord}
                className={`w-28 h-28 rounded-full flex items-center justify-center text-white shadow-lg transition-transform select-none touch-none ${
                  phase === "recording"
                    ? "bg-red-500 scale-105 ring-4 ring-red-200"
                    : "bg-emerald-600 hover:bg-emerald-700 active:scale-95"
                } disabled:opacity-50`}
                onPointerDown={(e) => {
                  e.preventDefault();
                  if (!canRecord) return;
                  beginRecording();
                }}
                onPointerUp={(e) => {
                  e.preventDefault();
                  if (phase === "recording") void finishRecordingAndSend();
                }}
                onPointerLeave={(e) => {
                  if (phase === "recording" && e.buttons === 0) void finishRecordingAndSend();
                }}
              >
                {micBusy ? (
                  <Loader2 className="w-10 h-10 animate-spin" />
                ) : (
                  <Mic className="w-10 h-10" />
                )}
              </button>
              <p className="text-xs text-muted-foreground text-center">
                Hold to speak, release to send. Use headphones so speaker audio is not picked up by your mic.
              </p>
              <Button variant="outline" className="w-full" onClick={endCall}>
                <PhoneOff className="w-4 h-4 mr-2" />
                End call
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
