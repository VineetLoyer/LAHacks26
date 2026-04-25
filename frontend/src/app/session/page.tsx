"use client";

import { useSearchParams } from "next/navigation";
import { useState, useEffect, Suspense } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { submitQuestion } from "@/lib/api";
import { getSocket, joinRoom } from "@/lib/socket";

function SessionContent() {
  const params = useSearchParams();
  const sessionId = params.get("id") || "";
  const sessionCode = params.get("code") || "";
  const sessionTitle = params.get("title") || "Session";

  const [question, setQuestion] = useState("");
  const [submitted, setSubmitted] = useState<string[]>([]);
  const [checkinOpen, setCheckinOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (sessionCode) {
      joinRoom(sessionCode, "student");
      const socket = getSocket();
      socket.on("checkin_requested", () => setCheckinOpen(true));
      return () => {
        socket.off("checkin_requested");
      };
    }
  }, [sessionCode]);

  async function handleSubmitQuestion() {
    if (!question.trim()) return;
    setLoading(true);
    try {
      await submitQuestion({ session_id: sessionId, text: question.trim() });
      setSubmitted((prev) => [question.trim(), ...prev]);
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
        <Card className="mb-6 border-amber-500">
          <CardHeader>
            <CardTitle>How confused are you right now?</CardTitle>
          </CardHeader>
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
                  onClick={() => setCheckinOpen(false)}
                  className="flex flex-col items-center p-3 rounded-lg hover:bg-muted transition-colors"
                >
                  <span className="text-3xl">{opt.emoji}</span>
                  <span className="text-xs mt-1">{opt.label}</span>
                </button>
              ))}
            </div>
          </CardContent>
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
