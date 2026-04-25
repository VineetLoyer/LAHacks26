"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { joinSession, verifyWorldId } from "@/lib/api";
import WorldIdGate from "@/components/world-id-gate";

type SessionInfo = {
  id: string;
  title: string;
  anonymous_mode: boolean;
  current_slide: number;
  demo_mode: boolean;
};

export default function JoinPage() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Two-step flow state
  const [step, setStep] = useState<"enter-code" | "verify">("enter-code");
  const [sessionInfo, setSessionInfo] = useState<SessionInfo | null>(null);
  const [verifyError, setVerifyError] = useState("");

  // Step 1: Enter session code and look up the session
  async function handleJoin() {
    if (!code.trim() || code.trim().length < 6) {
      setError("Please enter a valid 6-character session code");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const session = await joinSession(code.trim());
      setSessionInfo(session);

      // If demo mode, skip verification and go straight to session
      if (session.demo_mode) {
        router.push(
          `/session?id=${session.id}&code=${code.trim().toUpperCase()}&title=${encodeURIComponent(session.title)}`
        );
      } else {
        // Show World ID verification step
        setStep("verify");
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Session not found");
    } finally {
      setLoading(false);
    }
  }

  // Step 2: World ID verification succeeded — call backend to verify proof
  async function handleVerificationSuccess(proof: object) {
    if (!sessionInfo) return;
    setVerifyError("");
    setLoading(true);
    try {
      await verifyWorldId({
        proof,
        session_code: code.trim().toUpperCase(),
      });
      // Verification passed — navigate to session
      router.push(
        `/session?id=${sessionInfo.id}&code=${code.trim().toUpperCase()}&title=${encodeURIComponent(sessionInfo.title)}`
      );
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Verification failed";
      setVerifyError(msg);
    } finally {
      setLoading(false);
    }
  }

  // Step 1: Enter code UI
  if (step === "enter-code") {
    return (
      <main className="flex items-center justify-center min-h-screen p-8">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">Join a Session</CardTitle>
            <p className="text-muted-foreground">
              Enter the code your host shared
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              placeholder="Enter session code (e.g. ABC123)"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              maxLength={6}
              className="text-center text-2xl font-mono tracking-widest"
              onKeyDown={(e) => {
                if (e.key === "Enter") handleJoin();
              }}
            />
            {error && <p className="text-sm text-red-500">{error}</p>}
            <Button
              onClick={handleJoin}
              disabled={loading}
              className="w-full"
              size="lg"
            >
              {loading ? "Joining..." : "Join Session"}
            </Button>
          </CardContent>
        </Card>
      </main>
    );
  }

  // Step 2: World ID verification
  return (
    <main className="flex items-center justify-center min-h-screen p-8">
      <div className="w-full max-w-md space-y-4">
        {/* Back button */}
        <button
          onClick={() => {
            setStep("enter-code");
            setVerifyError("");
          }}
          className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
        >
          ← Back to code entry
        </button>

        {/* Session info */}
        {sessionInfo && (
          <div className="text-center mb-2">
            <p className="text-sm text-muted-foreground">
              Joining: <span className="font-medium text-foreground">{sessionInfo.title}</span>
            </p>
          </div>
        )}

        {/* World ID Gate */}
        <div className="flex justify-center">
          <WorldIdGate
            onSuccess={handleVerificationSuccess}
            onSkip={() => {
              if (sessionInfo) {
                router.push(
                  `/session?id=${sessionInfo.id}&code=${code.trim().toUpperCase()}&title=${encodeURIComponent(sessionInfo.title)}`
                );
              }
            }}
            demoMode={sessionInfo?.demo_mode ?? false}
          />
        </div>

        {/* Verification error with retry */}
        {verifyError && (
          <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-center">
            <p className="text-sm text-red-700">{verifyError}</p>
            <Button
              variant="outline"
              size="sm"
              className="mt-2"
              onClick={() => setVerifyError("")}
            >
              Try again
            </Button>
          </div>
        )}

        {loading && (
          <p className="text-sm text-center text-muted-foreground">
            Verifying...
          </p>
        )}
      </div>
    </main>
  );
}
