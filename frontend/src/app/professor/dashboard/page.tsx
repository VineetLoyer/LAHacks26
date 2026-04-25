"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { ConfusionGauge } from "@/components/confusion-gauge";
import { AnimatedCounter } from "@/components/animated-counter";
import { LiveIndicator } from "@/components/live-indicator";
import { SpikeAlert } from "@/components/spike-alert";
import {
  getSessionStats,
  getConfusionStats,
  listClusters,
  generateClusters,
  addressCluster,
} from "@/lib/api";
import { getSocket, joinRoom, triggerCheckin } from "@/lib/socket";
import {
  Users,
  MessageSquare,
  Sparkles,
  Loader2,
  CheckCircle2,
  ArrowUpCircle,
  Radio,
} from "lucide-react";

interface ClusterData {
  id: string;
  label: string;
  question_count: number;
  representative_question: string;
  on_topic: boolean;
  upvotes: number;
  status: string;
  ai_explanation: string | null;
  professor_response: string | null;
  response_type: string | null;
}

interface TimelineEntry {
  slide: number;
  confusion_pct: number;
  avg_rating: number;
  responses: number;
}

function DashboardContent() {
  const params = useSearchParams();
  const sessionId = params.get("id") || "";
  const sessionCode = params.get("code") || "";

  // --- State ---
  const [confusionIndex, setConfusionIndex] = useState(0);
  const [participantCount, setParticipantCount] = useState(0);
  const [questionCount, setQuestionCount] = useState(0);
  const [threshold, setThreshold] = useState(60);
  const [demoMode, setDemoMode] = useState(false);
  const [spikeAlert, setSpikeAlert] = useState({ visible: false, message: "" });
  const [clusters, setClusters] = useState<ClusterData[]>([]);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [clusterLoading, setClusterLoading] = useState(false);
  const [checkinInProgress, setCheckinInProgress] = useState(false);
  const [currentSlide, setCurrentSlide] = useState(1);
  const [addressingCluster, setAddressingCluster] = useState<ClusterData | null>(null);
  const [addressResponseType, setAddressResponseType] = useState("explained_now");
  const [customResponse, setCustomResponse] = useState("");
  const [addressLoading, setAddressLoading] = useState(false);

  // --- Fetch initial data ---
  useEffect(() => {
    if (!sessionId) return;

    getSessionStats(sessionId)
      .then((stats) => {
        setConfusionIndex(stats.confusion_index);
        setQuestionCount(stats.total_questions);
        setParticipantCount(stats.participant_count);
        setDemoMode(stats.demo_mode);
        setThreshold(stats.confusion_threshold);
      })
      .catch(() => {});

    getConfusionStats(sessionId)
      .then((data) => setTimeline(data.timeline))
      .catch(() => {});

    listClusters(sessionId)
      .then((data) => setClusters(data.clusters))
      .catch(() => {});
  }, [sessionId]);

  // --- Socket.IO setup ---
  useEffect(() => {
    if (!sessionCode) return;

    const socket = getSocket();

    const onConfusionUpdate = (data: { confusion_index: number; total_checkins: number; slide: number }) => {
      setConfusionIndex(data.confusion_index);
      setThreshold((prev) => {
        if (data.confusion_index > prev) {
          setSpikeAlert({
            visible: true,
            message: `⚠️ Confusion spike detected on Slide ${data.slide} — ${data.confusion_index}%`,
          });
        }
        return prev;
      });
    };

    const onParticipantCount = (data: { count: number }) => {
      setParticipantCount(data.count);
    };

    const onQuestionSubmitted = (data: { total_questions: number }) => {
      setQuestionCount(data.total_questions);
    };

    const onClusterUpvoted = (data: { cluster_id: string; upvotes: number }) => {
      setClusters((prev) =>
        prev.map((c) => (c.id === data.cluster_id ? { ...c, upvotes: data.upvotes } : c))
      );
    };

    // Remove any previous listeners to avoid duplicates (React strict mode)
    socket.off("confusion_update", onConfusionUpdate);
    socket.off("participant_count", onParticipantCount);
    socket.off("question_submitted", onQuestionSubmitted);
    socket.off("cluster_upvoted", onClusterUpvoted);

    socket.on("confusion_update", onConfusionUpdate);
    socket.on("participant_count", onParticipantCount);
    socket.on("question_submitted", onQuestionSubmitted);
    socket.on("cluster_upvoted", onClusterUpvoted);

    joinRoom(sessionCode, "professor");

    return () => {
      socket.off("confusion_update", onConfusionUpdate);
      socket.off("participant_count", onParticipantCount);
      socket.off("question_submitted", onQuestionSubmitted);
      socket.off("cluster_upvoted", onClusterUpvoted);
    };
  }, [sessionCode]);

  // --- Handlers ---
  const handleTriggerCheckin = useCallback(() => {
    triggerCheckin(sessionCode, currentSlide);
    setCheckinInProgress(true);
    setTimeout(() => setCheckinInProgress(false), 30000);
  }, [sessionCode, currentSlide]);

  const handleGenerateClusters = useCallback(async () => {
    setClusterLoading(true);
    try {
      const data = await generateClusters(sessionId);
      setClusters(
        data.clusters.map((c) => ({
          ...c,
          upvotes: 0,
          status: "pending",
          ai_explanation: null,
          professor_response: null,
          response_type: null,
        }))
      );
    } catch {
      // keep existing clusters on error
    } finally {
      setClusterLoading(false);
    }
  }, [sessionId]);

  const handleAddressCluster = useCallback((cluster: ClusterData) => {
    setAddressingCluster(cluster);
    setAddressResponseType("explained_now");
    setCustomResponse("");
  }, []);

  const handleConfirmAddress = useCallback(async () => {
    if (!addressingCluster) return;
    setAddressLoading(true);
    try {
      const result = await addressCluster({
        cluster_id: addressingCluster.id,
        response_type: addressResponseType,
        custom_response: addressResponseType === "text_response" ? customResponse : undefined,
      });
      setClusters((prev) =>
        prev.map((c) =>
          c.id === addressingCluster.id
            ? {
                ...c,
                status: "addressed",
                ai_explanation: result.ai_explanation,
                response_type: result.response_type,
                professor_response: addressResponseType === "text_response" ? customResponse : null,
              }
            : c
        )
      );
      setAddressingCluster(null);
    } catch {
      // keep modal open on error
    } finally {
      setAddressLoading(false);
    }
  }, [addressingCluster, addressResponseType, customResponse]);

  const handleDismissSpike = useCallback(() => {
    setSpikeAlert({ visible: false, message: "" });
  }, []);

  // Sort clusters by question_count descending
  const sortedClusters = [...clusters].sort((a, b) => b.question_count - a.question_count);

  return (
    <main className="min-h-screen p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Host Dashboard</h1>
            <p className="text-muted-foreground text-sm">Session ID: {sessionId}</p>
          </div>
          <div className="flex items-center gap-4">
            {demoMode && (
              <Badge variant="secondary" className="text-xs">
                Demo Mode
              </Badge>
            )}
            <div className="text-right">
              <div className="flex items-center justify-end gap-2">
                <p className="text-4xl font-mono font-bold tracking-widest">
                  {sessionCode}
                </p>
                <LiveIndicator />
              </div>
              <p className="text-xs text-muted-foreground">
                Share this code with participants
              </p>
            </div>
          </div>
        </div>

        {/* Spike Alert */}
        <SpikeAlert
          message={spikeAlert.message}
          visible={spikeAlert.visible}
          onDismiss={handleDismissSpike}
        />

        {/* Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Confusion Gauge */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Confusion Index
                <Badge variant="outline">Live</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="flex justify-center">
              <ConfusionGauge value={confusionIndex} threshold={threshold} />
            </CardContent>
          </Card>

          {/* Participants */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-4 w-4" />
                Participants
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-6xl font-bold text-center py-8">
                <AnimatedCounter value={participantCount} />
              </div>
              <p className="text-center text-sm text-muted-foreground">
                Participants connected
              </p>
            </CardContent>
          </Card>

          {/* Questions */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="h-4 w-4" />
                Questions
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-6xl font-bold text-center py-8">
                <AnimatedCounter value={questionCount} />
              </div>
              <p className="text-center text-sm text-muted-foreground">
                Questions submitted
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Controls Row */}
        <Card>
          <CardContent className="flex flex-wrap items-center gap-4 pt-4">
            {/* Trigger Check-in */}
            <div className="flex items-center gap-2">
              <label htmlFor="slide-input" className="text-sm font-medium whitespace-nowrap">
                Slide #
              </label>
              <Input
                id="slide-input"
                type="number"
                min={1}
                value={currentSlide}
                onChange={(e) => setCurrentSlide(Number(e.target.value) || 1)}
                className="w-20"
              />
              <Button onClick={handleTriggerCheckin} disabled={checkinInProgress}>
                {checkinInProgress ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Check-in in progress...
                  </>
                ) : (
                  <>
                    <Radio className="h-4 w-4" />
                    Trigger Check-in
                  </>
                )}
              </Button>
            </div>

            {/* Generate Clusters */}
            <Button
              variant="secondary"
              onClick={handleGenerateClusters}
              disabled={clusterLoading}
            >
              {clusterLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  AI is analyzing questions...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  Generate Clusters
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Clusters Section */}
        <div>
          <h2 className="text-xl font-semibold mb-4">Question Clusters</h2>
          {sortedClusters.length === 0 ? (
            <Card>
              <CardContent>
                <p className="text-muted-foreground text-center py-12">
                  {clusterLoading
                    ? "AI is analyzing questions..."
                    : "Clusters will appear here after participants submit questions and you trigger AI clustering."}
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {sortedClusters.map((cluster, index) => (
                <Card
                  key={cluster.id}
                  className={
                    cluster.status === "addressed"
                      ? "opacity-70 border-green-500/30"
                      : ""
                  }
                  style={{
                    animation: `fadeInUp 0.4s ease-out ${index * 100}ms both`,
                  }}
                >
                  <style>{`
                    @keyframes fadeInUp {
                      from {
                        opacity: 0;
                        transform: translateY(12px);
                      }
                      to {
                        opacity: 1;
                        transform: translateY(0);
                      }
                    }
                  `}</style>
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between text-base">
                      <span className="flex items-center gap-2">
                        {cluster.status === "addressed" && (
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                        )}
                        {cluster.label}
                      </span>
                      <div className="flex items-center gap-2">
                        <Badge variant={cluster.on_topic ? "default" : "secondary"}>
                          {cluster.on_topic ? "On Topic" : "Off Topic"}
                        </Badge>
                      </div>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <p className="text-sm text-muted-foreground italic">
                      &ldquo;{cluster.representative_question}&rdquo;
                    </p>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <span>{cluster.question_count} questions</span>
                        <span className="flex items-center gap-1">
                          <ArrowUpCircle className="h-3.5 w-3.5" />
                          {cluster.upvotes}
                        </span>
                      </div>
                      {cluster.status === "pending" && (
                        <Button
                          size="sm"
                          onClick={() => handleAddressCluster(cluster)}
                        >
                          Address
                        </Button>
                      )}
                      {cluster.status === "addressed" && (
                        <span className="text-xs text-green-600 font-medium">
                          Addressed
                        </span>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Address Cluster Modal */}
        <Dialog
          open={addressingCluster !== null}
          onOpenChange={(open) => {
            if (!open) setAddressingCluster(null);
          }}
        >
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle>Address: {addressingCluster?.label}</DialogTitle>
              <DialogDescription>
                {addressingCluster?.question_count} questions &middot; &ldquo;
                {addressingCluster?.representative_question}&rdquo;
              </DialogDescription>
            </DialogHeader>

            {addressingCluster?.ai_explanation && (
              <div className="rounded-lg bg-muted p-3 text-sm">
                <p className="font-medium mb-1">AI Explanation</p>
                <p className="text-muted-foreground">
                  {addressingCluster.ai_explanation}
                </p>
              </div>
            )}

            <div className="space-y-3">
              <p className="text-sm font-medium">Response Type</p>
              <div className="space-y-2">
                {[
                  { value: "explained_now", label: "Explain Now" },
                  { value: "flagged_next_class", label: "Flag for Next Class" },
                  { value: "text_response", label: "Custom Text Response" },
                ].map((option) => (
                  <label
                    key={option.value}
                    className="flex items-center gap-2 cursor-pointer"
                  >
                    <input
                      type="radio"
                      name="response_type"
                      value={option.value}
                      checked={addressResponseType === option.value}
                      onChange={(e) => setAddressResponseType(e.target.value)}
                      className="accent-primary"
                    />
                    <span className="text-sm">{option.label}</span>
                  </label>
                ))}
              </div>

              {addressResponseType === "text_response" && (
                <Input
                  placeholder="Type your response..."
                  value={customResponse}
                  onChange={(e) => setCustomResponse(e.target.value)}
                />
              )}
            </div>

            <DialogFooter>
              <Button
                onClick={handleConfirmAddress}
                disabled={addressLoading}
              >
                {addressLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Sending...
                  </>
                ) : (
                  "Confirm & Broadcast"
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </main>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<div className="p-8">Loading dashboard...</div>}>
      <DashboardContent />
    </Suspense>
  );
}
