"use client";

import { useSearchParams } from "next/navigation";
import { useState, useEffect, useCallback, Suspense } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { submitQuestion, submitCheckin, listClusters, upvoteCluster, downvoteCluster, optInEmail, submitFeedback } from "@/lib/api";
import { getSocket, joinRoom } from "@/lib/socket";
import { BroadcastFeed, type Broadcast } from "@/components/broadcast-feed";
import { WhisperButton } from "@/components/whisper-button";
import { ArrowUpCircle, Mail } from "lucide-react";

const STORAGE_KEY_PREFIX = "asksafe_questions_";
const EMAIL_OPTIN_KEY_PREFIX = "asksafe_email_optin_";
const FEEDBACK_KEY_PREFIX = "asksafe_feedback_";

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

const UPVOTE_KEY_PREFIX = "asksafe_upvotes_";

interface ClusterData {
  id: string;
  label: string;
  question_count: number;
  representative_question: string;
  summary: string;
  upvotes: number;
  status: string;
  on_topic: boolean;
  ai_explanation: string | null;
  professor_response: string | null;
  response_type: string | null;
}

function getUpvotedIds(code: string): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(`${UPVOTE_KEY_PREFIX}${code}`);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function storeUpvotedIds(code: string, ids: string[]) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(`${UPVOTE_KEY_PREFIX}${code}`, JSON.stringify(ids));
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
  const [clusters, setClusters] = useState<ClusterData[]>([]);
  const [upvotedIds, setUpvotedIds] = useState<string[]>([]);
  const [currentSlide, setCurrentSlide] = useState<number | undefined>(undefined);
  const [emailInput, setEmailInput] = useState("");
  const [emailOptedIn, setEmailOptedIn] = useState(false);
  const [emailLoading, setEmailLoading] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [sessionEnded, setSessionEnded] = useState(false);
  const [feedbackRating, setFeedbackRating] = useState<number | null>(null);
  const [feedbackComment, setFeedbackComment] = useState("");
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [feedbackLoading, setFeedbackLoading] = useState(false);

  // Restore submitted questions, upvoted IDs, and email opt-in from localStorage, fetch clusters on mount
  useEffect(() => {
    if (sessionCode) {
      const stored = getStoredQuestions(sessionCode);
      if (stored.length > 0) {
        setSubmitted(stored);
      }
      setUpvotedIds(getUpvotedIds(sessionCode));
      // Restore email opt-in status
      try {
        const optedIn = localStorage.getItem(`${EMAIL_OPTIN_KEY_PREFIX}${sessionCode}`);
        if (optedIn) {
          setEmailOptedIn(true);
        }
        // Restore feedback submission status
        const feedbackDone = localStorage.getItem(`${FEEDBACK_KEY_PREFIX}${sessionCode}`);
        if (feedbackDone) {
          setFeedbackSubmitted(true);
        }
      } catch {
        // localStorage unavailable
      }
    }
    if (sessionId) {
      listClusters(sessionId)
        .then((data) => setClusters(data.clusters))
        .catch(() => {});
    }
  }, [sessionCode, sessionId]);

  // Socket.IO setup
  useEffect(() => {
    if (!sessionCode) return;

    const socket = getSocket();

    const handleCheckinRequested = (data: { slide?: number }) => {
      setCheckinSlide(data?.slide ?? 0);
      if (data?.slide) setCurrentSlide(data.slide);
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

    const handleClusterUpvoted = (data: { cluster_id: string; upvotes: number }) => {
      setClusters((prev) =>
        prev.map((c) => (c.id === data.cluster_id ? { ...c, upvotes: data.upvotes } : c))
      );
    };

    const handleClustersUpdated = (data: { clusters: ClusterData[] }) => {
      // Merge new clusters with existing ones (replace matching IDs, add new ones)
      setClusters((prev) => {
        const existingIds = new Set(prev.map((c) => c.id));
        const newClusters = data.clusters.filter((c) => !existingIds.has(c.id));
        return [...prev, ...newClusters];
      });
    };

    const handleSessionEnded = () => {
      setSessionEnded(true);
    };

    // Remove previous listeners to avoid duplicates (React strict mode)
    socket.off("checkin_requested", handleCheckinRequested);
    socket.off("cluster_addressed", handleClusterAddressed);
    socket.off("cluster_upvoted", handleClusterUpvoted);
    socket.off("clusters_updated", handleClustersUpdated);
    socket.off("session_ended", handleSessionEnded);

    socket.on("checkin_requested", handleCheckinRequested);
    socket.on("cluster_addressed", handleClusterAddressed);
    socket.on("cluster_upvoted", handleClusterUpvoted);
    socket.on("clusters_updated", handleClustersUpdated);
    socket.on("session_ended", handleSessionEnded);

    joinRoom(sessionCode, "student");

    return () => {
      socket.off("checkin_requested", handleCheckinRequested);
      socket.off("cluster_addressed", handleClusterAddressed);
      socket.off("cluster_upvoted", handleClusterUpvoted);
      socket.off("clusters_updated", handleClustersUpdated);
      socket.off("session_ended", handleSessionEnded);
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

  async function handleToggleUpvote(clusterId: string) {
    const isUpvoted = upvotedIds.includes(clusterId);
    try {
      if (isUpvoted) {
        // Downvote (remove upvote)
        await downvoteCluster(clusterId);
        const updated = upvotedIds.filter((id) => id !== clusterId);
        setUpvotedIds(updated);
        storeUpvotedIds(sessionCode, updated);
        setClusters((prev) =>
          prev.map((c) => (c.id === clusterId ? { ...c, upvotes: Math.max(0, c.upvotes - 1) } : c))
        );
      } else {
        // Upvote
        await upvoteCluster(clusterId);
        const updated = [...upvotedIds, clusterId];
        setUpvotedIds(updated);
        storeUpvotedIds(sessionCode, updated);
        setClusters((prev) =>
          prev.map((c) => (c.id === clusterId ? { ...c, upvotes: c.upvotes + 1 } : c))
        );
      }
    } catch {
      // silently fail
    }
  }

  async function handleSubmitQuestion() {
    if (!question.trim()) return;
    setLoading(true);
    try {
      await submitQuestion({ session_id: sessionId, text: question.trim(), slide: currentSlide });
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

  async function handleEmailOptIn() {
    if (!emailInput.trim()) return;
    setEmailLoading(true);
    setEmailError(null);
    try {
      await optInEmail(sessionId, emailInput.trim());
      setEmailOptedIn(true);
      try {
        localStorage.setItem(`${EMAIL_OPTIN_KEY_PREFIX}${sessionCode}`, emailInput.trim());
      } catch {
        // localStorage unavailable
      }
    } catch (err) {
      setEmailError(err instanceof Error ? err.message : "Failed to subscribe");
    } finally {
      setEmailLoading(false);
    }
  }

  async function handleSubmitFeedback() {
    if (feedbackRating === null) return;
    setFeedbackLoading(true);
    try {
      await submitFeedback(sessionId, {
        rating: feedbackRating,
        comment: feedbackComment.trim() || undefined,
      });
      setFeedbackSubmitted(true);
      try {
        localStorage.setItem(`${FEEDBACK_KEY_PREFIX}${sessionCode}`, "1");
      } catch {
        // localStorage unavailable
      }
    } catch {
      // silently fail
    } finally {
      setFeedbackLoading(false);
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
            <WhisperButton
              onTranscript={(text) => setQuestion((prev) => (prev ? prev + " " + text : text))}
              disabled={loading}
            />
            <Button onClick={handleSubmitQuestion} disabled={loading}>
              {loading ? "..." : "Send"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Broadcast Feed */}
      <BroadcastFeed broadcasts={broadcasts} />

      {/* Cluster Upvoting */}
      {(() => {
        const activeClusters = clusters
          .filter((c) => c.status !== "hidden")
          .sort((a, b) => b.upvotes - a.upvotes);
        if (activeClusters.length === 0) return null;
        return (
          <div className="mb-6 space-y-3">
            <h2 className="text-lg font-semibold">Popular Questions</h2>
            {activeClusters.map((cluster) => (
              <Card key={cluster.id}>
                <CardContent className="flex items-start justify-between gap-3 pt-4">
                  <div className="flex-1 min-w-0 space-y-1">
                    <p className="font-bold text-sm">{cluster.label}</p>
                    <p className="text-sm text-muted-foreground">
                      {cluster.summary || cluster.representative_question}
                    </p>
                    <div className="flex items-center gap-2">
                      <Badge variant={cluster.on_topic ? "default" : "secondary"}>
                        {cluster.on_topic ? "On-topic" : "Off-topic"}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {cluster.question_count} question{cluster.question_count !== 1 ? "s" : ""}
                      </span>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleToggleUpvote(cluster.id)}
                    className={`flex items-center gap-1 shrink-0 ${upvotedIds.includes(cluster.id) ? "text-primary" : ""}`}
                  >
                    <ArrowUpCircle className="h-4 w-4" />
                    <span>{cluster.upvotes}</span>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        );
      })()}

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

      {/* Session Ended — Feedback + Email Opt-in */}
      {sessionEnded && (
        <Card className="mb-6 border-blue-500 bg-blue-50 dark:bg-blue-950">
          <CardContent className="pt-4 space-y-4">
            {/* Feedback Form */}
            {!feedbackSubmitted ? (
              <div className="space-y-3">
                <p className="text-sm font-semibold text-blue-700 dark:text-blue-300 text-center">
                  Session Ended — How was this lecture?
                </p>
                {/* Star Rating */}
                <div className="flex justify-center gap-2">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      onClick={() => setFeedbackRating(star)}
                      className="text-3xl transition-transform hover:scale-110 focus:outline-none"
                      aria-label={`Rate ${star} star${star !== 1 ? "s" : ""}`}
                    >
                      {feedbackRating !== null && star <= feedbackRating ? "★" : "☆"}
                    </button>
                  ))}
                </div>
                {feedbackRating !== null && (
                  <p className="text-xs text-muted-foreground text-center">
                    {feedbackRating === 1 && "Poor"}
                    {feedbackRating === 2 && "Fair"}
                    {feedbackRating === 3 && "Good"}
                    {feedbackRating === 4 && "Very Good"}
                    {feedbackRating === 5 && "Excellent"}
                  </p>
                )}
                {/* Optional Comment */}
                <textarea
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="Any comments for the professor? (optional)"
                  rows={2}
                  value={feedbackComment}
                  onChange={(e) => setFeedbackComment(e.target.value)}
                />
                <div className="flex justify-center">
                  <Button
                    onClick={handleSubmitFeedback}
                    disabled={feedbackRating === null || feedbackLoading}
                    size="sm"
                  >
                    {feedbackLoading ? "Submitting..." : "Submit Feedback"}
                  </Button>
                </div>
              </div>
            ) : (
              <p className="text-sm text-green-600 dark:text-green-400 font-medium text-center">
                ✅ Thanks for your feedback!
              </p>
            )}

            {/* Divider */}
            <div className="border-t border-blue-200 dark:border-blue-800" />

            {/* Email opt-in */}
            {emailOptedIn ? (
              <p className="text-sm text-green-600 dark:text-green-400 text-center">
                ✅ You&apos;ll receive a summary at your email shortly.
              </p>
            ) : (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground text-center">
                  Want a summary of today&apos;s session? Enter your email below.
                </p>
                <div className="flex gap-2 max-w-md mx-auto">
                  <Input
                    type="email"
                    placeholder="your@email.com"
                    value={emailInput}
                    onChange={(e) => setEmailInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleEmailOptIn()}
                    disabled={emailLoading}
                  />
                  <Button
                    onClick={handleEmailOptIn}
                    disabled={emailLoading || !emailInput.trim()}
                    size="sm"
                  >
                    {emailLoading ? "..." : "Send me summary"}
                  </Button>
                </div>
                {emailError && (
                  <p className="text-sm text-destructive text-center">{emailError}</p>
                )}
              </div>
            )}
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
