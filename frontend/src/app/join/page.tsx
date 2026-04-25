"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { joinSession } from "@/lib/api";

export default function JoinPage() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleJoin() {
    if (!code.trim() || code.trim().length < 6) {
      setError("Please enter a valid 6-character session code");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const session = await joinSession(code.trim());
      router.push(
        `/session?id=${session.id}&code=${code.trim().toUpperCase()}&title=${encodeURIComponent(session.title)}`
      );
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Session not found");
    } finally {
      setLoading(false);
    }
  }

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
