"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { createSession } from "@/lib/api";

export default function ProfessorPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [anonymousMode, setAnonymousMode] = useState(true);
  const [threshold, setThreshold] = useState([60]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleCreate() {
    if (!title.trim()) {
      setError("Please enter a session title");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const session = await createSession({
        title: title.trim(),
        anonymous_mode: anonymousMode,
        confusion_threshold: threshold[0],
      });
      router.push(`/professor/dashboard?id=${session.id}&code=${session.code}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create session");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex items-center justify-center min-h-screen p-8">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle className="text-2xl">Create a Session</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <label className="text-sm font-medium mb-2 block">
              Session Title
            </label>
            <Input
              placeholder="e.g. CS101 — Recursion"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          <div>
            <label className="text-sm font-medium mb-2 block">
              Confusion Alert Threshold: {threshold[0]}%
            </label>
            <Slider
              value={threshold}
              onValueChange={(val) => setThreshold(Array.isArray(val) ? val : [val])}
              min={10}
              max={100}
              step={5}
            />
            <p className="text-xs text-muted-foreground mt-1">
              Alert fires when confusion exceeds this percentage
            </p>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="anon"
              checked={anonymousMode}
              onChange={(e) => setAnonymousMode(e.target.checked)}
              className="h-4 w-4"
            />
            <label htmlFor="anon" className="text-sm">
              Anonymous Mode (no participant data stored)
            </label>
          </div>

          {error && <p className="text-sm text-red-500">{error}</p>}

          <Button
            onClick={handleCreate}
            disabled={loading}
            className="w-full"
            size="lg"
          >
            {loading ? "Creating..." : "Create Session"}
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}
