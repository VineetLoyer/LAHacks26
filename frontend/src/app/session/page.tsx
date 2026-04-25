"use client";

import { useSearchParams } from "next/navigation";
import { useState, useEffect, useCallback, Suspense } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { submitQuestion, submitCheckin } from "@/lib/api";
import { getSocket, joinRoom } from "@/lib/socket";
import { BroadcastFeed, type Broadcast } from "@/components/broadcast-feed";

const STORAGE_KEY_PREFIX = "asksafe_questions_";

function getStoredQuestions(code: string): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY_PREFIX}${code}`);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function storeQuestions(code: string, questions: string[]) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(
      `${STORAGE_KEY_PREFIX}${code}`,
      JSON.stringify(questions)
    );
  } catch {
    // localStorage full or unavailable — silently ignore
  }
}

function SessionContent() {
  const params = useSearchParams();
  const sessionId = params.get("id") || "";
  const sessionCode = params.get("code") || "";
  const sessionTitle = params.get("title") || "Session";

  const [question, setQuestion] = useState("");
  const [submitted, setSubmitted] = useState<string[]>([]);
  const [checkinOpen, setCheckinOpen] = useState(false);
  const [checkinSlide, setCheckinSlide] = useState<number>(0);
  const [checkinLoading, setCheckinLoading] = useState(false);
  const [checkinError, setCheckinError] = useState<string | null>(null);
  const [checkinSuccess, setCheckinSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const [broadcasts, setBroadcasts] = useState<Broadcast[]>([]);

  // Restore submitted questions from localStorage on mount
  useEffect(() => {
    if (sessionCode) {
      const stored = getStoredQuestions(sessionCode);
      if (stored.length > 0) {
        setSubmitted(stored);
      }
    }
  }, [sessionCode]);

  // Socket.IO setup
  useEffect(() => {
    if (!sessionCode) return;

    joinRoom(sessionCode, "student");
    const socket = getSocket();

    const handleCheckinRequested = (data: { slide?: number }) => {
      setCheckinSlide(data?.slide ?? 0);
      setCheckinError(null);
      setCheckinSuccess(false);
      setCheckinOpen(true);
    };

    const handleClusterAddressed = (data: {
      cluster_id: string;
      label: string;
      ai_explanation: string;
      professor_response: string | null;
      response_type: string;
    }) => {
      const broadcast: Broadcast = {
        ...data,
        timestamp: new Date().toISOString(),
      };
      setBroadcasts((prev) => [broadcast, ...prev]);
    };

    socket.on("checkin_requested", handleCheckinRequested);
    socket.on("cluster_addressed", handleClusterAddressed);

    return () => {
      socket.off("checkin_requested", handleCheckinRequested);
      socket.off("cluster_addressed", handleClusterAddressed);
    };
  }, [sessionCode]);

  const handleCheckinSubmit = useCallback(
    async (rating: number) => {
      setCheckinLoading(true);
      setCheckinError(null);
      try {
        await submitCheckin({
          session_id: sessionId,
          confusion_rating: rating,
          slide: checkinSlide,
        });
        setCheckinSuccess(true);
        // Show success toast for 2 seconds then close
        setTimeout(() => {
          setCheckinOpen(false);
          setCheckinSuccess(false);
        }, 2000);
      } catch (err) {
        setCheckinError(
          err instanceof Error ? err.message : "Failed to submit. Try again."
        );
      } finally {
        setCheckinLoading(false);
      }
    },
    [sessionId, checkinSlide]
  );

  async function handleSubmitQuestion() {
    if (!question.trim()) return;
    setLoading(true);
    try {
      await submitQuestion({ session_id: sessionId, text: question.trim() });
      const updated = [question.trim(), ...submitted];
      setSubmitted(updated);
      storeQuestions(sessionCode, updated);
      setQuestion("");
    } catch {
      // silently fail for now
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen p-6 max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">{sessionTitle}</h1>
        <Badge variant="outline" className="mt-1">
          Code: {sessionCode}
        </Badge>
      </div>

      {/* Confusion Check-in Modal */}
      {checkinOpen && (
        <Card className="mb-6 border-amber-500 checkin-slide-up">
          <CardHeader>
            <CardTitle>
              {checkinSuccess
                ? "✓ Submitted"
                : "How confused are you right now?"}
            </CardTitle>
          </CardHeader>
          {!checkinSuccess && (
            <CardContent>
              <div className="flex gap-3 justify-center">
                {[
                  { val: 1, emoji: "😊", label: "Clear" },
                  { val: 2, emoji: "🙂", label: "Mostly clear" },
                  { val: 3, emoji: "😐", label: "Somewhat" },
                  { val: 4, emoji: "😕", label: "Confused" },
                  { val: 5, emoji: "😵", label: "Very confused" },
                ].map((opt) => (
                  <button
                    key={opt.val}
                    onClick={() => handleCheckinSubmit(opt.val)}
                    disabled={checkinLoading}
                    className="emoji-btn flex flex-col items-center p-3 rounded-lg hover:bg-muted transition-colors disabled:opacity-50"
                  >
                    <span className="text-3xl">{opt.emoji}</span>
                    <span className="text-xs mt-1">{opt.label}</span>
                  </button>
                ))}
              </div>
              {checkinError && (
                <p className="mt-3 text-sm text-destructive text-center">
                  {checkinError}
                </p>
              )}
            </CardContent>
          )}
        </Card>
      )}

      {/* Question Submission */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Ask a Question</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              placeholder="Type your question anonymously..."
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSubmitQuestion()}
            />
            <Button onClick={handleSubmitQuestion} disabled={loading}>
              {loading ? "..." : "Send"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Broadcast Feed */}
      <BroadcastFeed broadcasts={broadcasts} />

      {/* Submitted Questions */}
      {submitted.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Your Questions</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {submitted.map((q, i) => (
                <li key={i} className="text-sm p-2 bg-muted rounded">
                  {q}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </main>
  );
}

export default function SessionPage() {
  return (
    <Suspense fallback={<div className="p-8">Loading session...</div>}>
      <SessionContent />
    </Suspense>
  );
}
