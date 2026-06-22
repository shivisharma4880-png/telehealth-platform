"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { useToast } from "@/components/ui/toaster";
import { Stethoscope, Phone, Mail, Lock, ArrowRight, Loader2 } from "lucide-react";

type Mode = "select" | "patient-phone" | "patient-otp" | "clinician-email";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuthStore();
  const { toast } = useToast();
  const [mode, setMode] = useState<Mode>("select");
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [requiresTotp, setRequiresTotp] = useState(false);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [isNewUser, setIsNewUser] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSendOtp() {
    if (!phone.trim()) return;
    setLoading(true);
    try {
      await api.post("/auth/otp/request", { phone });
      setMode("patient-otp");
      toast({ title: "OTP sent", description: `OTP sent to ${phone}. In dev mode, use 123456.` });
    } catch (err: any) {
      toast({ title: "Error", description: err.message, variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyOtp() {
    if (!otp.trim()) return;
    setLoading(true);
    try {
      const res = await api.post<any>("/auth/otp/verify", {
        phone,
        otp,
        first_name: firstName || undefined,
        last_name: lastName || undefined,
      });
      login({ id: res.user_id, role: res.role, phone }, res.access_token, res.refresh_token);
      toast({ title: "Welcome!", description: "Logged in successfully." });
      router.push("/patient/home");
    } catch (err: any) {
      toast({ title: "Invalid OTP", description: err.message, variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }

  async function handleEmailLogin() {
    if (!email.trim() || !password.trim()) return;
    setLoading(true);
    try {
      const res = await api.post<any>("/auth/login", {
        email,
        password,
        totp_code: totpCode || undefined,
      });
      login({ id: res.user_id, role: res.role, email }, res.access_token, res.refresh_token);
      toast({ title: "Welcome back!", description: "Logged in successfully." });
      if (res.role === "admin") router.push("/admin/dashboard");
      else router.push("/clinician/dashboard");
    } catch (err: any) {
      if (err.status === 428) {
        setRequiresTotp(true);
        toast({ title: "2FA Required", description: "Enter your authenticator code." });
      } else {
        toast({ title: "Login failed", description: err.message, variant: "destructive" });
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 to-blue-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary rounded-2xl mb-4 shadow-lg">
            <Stethoscope className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">TeleHealth Platform</h1>
          <p className="text-gray-500 mt-1">AI-Powered Teleconsultation</p>
        </div>

        {mode === "select" && (
          <Card className="shadow-xl border-0">
            <CardHeader className="text-center">
              <CardTitle>Sign In</CardTitle>
              <CardDescription>Choose your login method</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button
                className="w-full h-14 text-base"
                onClick={() => setMode("patient-phone")}
              >
                <Phone className="mr-2" />
                Patient — Login with Phone OTP
              </Button>
              <Button
                variant="outline"
                className="w-full h-14 text-base"
                onClick={() => setMode("clinician-email")}
              >
                <Mail className="mr-2" />
                Doctor / Admin — Email Login
              </Button>
            </CardContent>
            <CardFooter className="justify-center text-sm text-muted-foreground">
              New patient?{" "}
              <button
                type="button"
                className="ml-1 text-primary hover:underline"
                onClick={() => setMode("patient-phone")}
              >
                Create account
              </button>
            </CardFooter>
          </Card>
        )}

        {mode === "patient-phone" && (
          <Card className="shadow-xl border-0">
            <CardHeader>
              <button onClick={() => setMode("select")} className="text-sm text-muted-foreground mb-2 flex items-center gap-1">
                ← Back
              </button>
              <CardTitle>Patient Login</CardTitle>
              <CardDescription>Enter your mobile number to receive an OTP</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Mobile Number</Label>
                <Input
                  placeholder="+91 98765 43210"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="mt-1"
                />
                <p className="text-xs text-muted-foreground mt-1">In development, any phone works. OTP will be 123456.</p>
              </div>
              <Button className="w-full" onClick={handleSendOtp} disabled={loading || !phone}>
                {loading ? <Loader2 className="animate-spin mr-2" /> : null}
                Send OTP
                <ArrowRight className="ml-2" />
              </Button>
            </CardContent>
          </Card>
        )}

        {mode === "patient-otp" && (
          <Card className="shadow-xl border-0">
            <CardHeader>
              <button onClick={() => setMode("patient-phone")} className="text-sm text-muted-foreground mb-2">
                ← Back
              </button>
              <CardTitle>Verify OTP</CardTitle>
              <CardDescription>Enter the 6-digit code sent to {phone}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>OTP Code</Label>
                <Input
                  placeholder="123456"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  maxLength={6}
                  className="mt-1 text-center text-2xl tracking-widest"
                />
              </div>
              {isNewUser && (
                <>
                  <div>
                    <Label>First Name</Label>
                    <Input value={firstName} onChange={(e) => setFirstName(e.target.value)} className="mt-1" />
                  </div>
                  <div>
                    <Label>Last Name</Label>
                    <Input value={lastName} onChange={(e) => setLastName(e.target.value)} className="mt-1" />
                  </div>
                </>
              )}
              <Button className="w-full" onClick={handleVerifyOtp} disabled={loading || otp.length !== 6}>
                {loading ? <Loader2 className="animate-spin mr-2" /> : null}
                Verify & Login
              </Button>
              <p className="text-xs text-center text-muted-foreground">
                New user?{" "}
                <button className="text-primary hover:underline" onClick={() => setIsNewUser(!isNewUser)}>
                  {isNewUser ? "Hide name fields" : "Enter your name to register"}
                </button>
              </p>
            </CardContent>
          </Card>
        )}

        {mode === "clinician-email" && (
          <Card className="shadow-xl border-0">
            <CardHeader>
              <button onClick={() => setMode("select")} className="text-sm text-muted-foreground mb-2">
                ← Back
              </button>
              <CardTitle>Doctor / Admin Login</CardTitle>
              <CardDescription>Use your email and password</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Email</Label>
                <Input
                  type="email"
                  placeholder="dr.patel@clinic.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <Label>Password</Label>
                <Input
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="mt-1"
                />
              </div>
              {requiresTotp && (
                <div>
                  <Label>Authenticator Code (2FA)</Label>
                  <Input
                    placeholder="123456"
                    value={totpCode}
                    onChange={(e) => setTotpCode(e.target.value)}
                    maxLength={6}
                    className="mt-1"
                  />
                </div>
              )}
              <Button className="w-full" onClick={handleEmailLogin} disabled={loading || !email || !password}>
                {loading ? <Loader2 className="animate-spin mr-2" /> : null}
                Sign In
                <Lock className="ml-2" />
              </Button>
              <div className="text-xs text-muted-foreground text-center">
                <p>Demo: dr.patel@clinic.com / doctor123</p>
                <p>Admin: admin@clinic.com / admin123</p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
