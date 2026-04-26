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
import { ConfusionChart } from "@/components/confusion-chart";
import {
  getSessionStats,
  getConfusionStats,
  listClusters,
  generateClusters,
  addressCluster,
  hideCluster,
  restoreCluster,
  generateReport,
} from "@/lib/api";
import type { ReportData } from "@/lib/api";
import { ReportView } from "@/components/report-view";
import { getSocket, joinRoom, triggerCheckin } from "@/lib/socket";
import {
  Users,
  MessageSquare,
  Sparkles,
  Loader2,
  CheckCircle2,
  ArrowUpCircle,
  Radio,
  StopCircle,
  EyeOff,
  Eye,
  RotateCcw,
} from "lucide-react";

interface ClusterData {
  id: string;
  label: string;
  question_count: number;
  representative_question: string;
  summary: string;
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
  const [aiDraft, setAiDraft] = useState("");
  const [aiDraftLoading, setAiDraftLoading] = useState(false);
  const [linkUrl, setLinkUrl] = useState("");

  // Report state
  const [report, setReport] = useState<ReportData | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [showReport, setShowReport] = useState(false);
  const [sessionTitle, setSessionTitle] = useState("");
  const [showHidden, setShowHidden] = useState(false);
  const [sessionEnded, setSessionEnded] = useState(false);

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

  // Periodic cluster refresh (fallback for intermittent Socket.IO upvote events)
  useEffect(() => {
    if (!sessionId) return;
    const interval = setInterval(() => {
      listClusters(sessionId)
        .then((data) => setClusters(data.clusters))
        .catch(() => {});
    }, 5000); // refresh every 5 seconds
    return () => clearInterval(interval);
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

      // Update timeline data in real-time
      setTimeline((prev) => {
        const existing = prev.find((entry) => entry.slide === data.slide);
        if (existing) {
          return prev.map((entry) =>
            entry.slide === data.slide
              ? { ...entry, confusion_pct: data.confusion_index, responses: data.total_checkins }
              : entry
          );
        }
        return [
          ...prev,
          { slide: data.slide, confusion_pct: data.confusion_index, avg_rating: 0, responses: data.total_checkins },
        ].sort((a, b) => a.slide - b.slide);
      });
    };

    const onParticipantCount = (data: { count: number }) => {
      setParticipantCount(data.count);
    };

    const onQuestionSubmitted = (data: { total_questions: number }) => {
      setQuestionCount(data.total_questions);
    };

    const onClusterUpvoted = (data: { cluster_id: string; upvotes: number }) => {
      console.log("[Socket] cluster_upvoted received:", data);
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
          summary: (c as ClusterData & { summary?: string }).summary || "",
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
    setAiDraft("");
    setAiDraftLoading(false);
    setLinkUrl("");
  }, []);

  const handleGenerateAiDraft = useCallback(async () => {
    if (!addressingCluster) return;
    setAiDraftLoading(true);
    try {
      // Call address with a dry-run-like approach — we'll use the result as a draft
      const result = await addressCluster({
        cluster_id: addressingCluster.id,
        response_type: "explained_now",
      });
      const draft = result.ai_explanation || "";
      setAiDraft(draft);
      setCustomResponse(draft);
      // Update the cluster status locally since the backend already marked it
      setClusters((prev) =>
        prev.map((c) =>
          c.id === addressingCluster.id
            ? { ...c, status: "addressed", ai_explanation: draft, response_type: "explained_now" }
            : c
        )
      );
    } catch {
      setAiDraft("Failed to generate AI suggestion. You can type your own response.");
    } finally {
      setAiDraftLoading(false);
    }
  }, [addressingCluster]);

  const handleConfirmAddress = useCallback(async () => {
    if (!addressingCluster) return;
    setAddressLoading(true);
    try {
      // Build the response based on selected type
      let responseText = customResponse;
      if (addressResponseType === "send_link") {
        responseText = linkUrl ? `📎 Resource: ${linkUrl}${customResponse ? `\n\n${customResponse}` : ""}` : customResponse;
      }

      const result = await addressCluster({
        cluster_id: addressingCluster.id,
        response_type: addressResponseType,
        custom_response: responseText || undefined,
      });
      setClusters((prev) =>
        prev.map((c) =>
          c.id === addressingCluster.id
            ? {
                ...c,
                status: addressResponseType === "flagged_next_class" ? "flagged" : "addressed",
                ai_explanation: result.ai_explanation,
                response_type: result.response_type,
                professor_response: responseText || null,
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
  }, [addressingCluster, addressResponseType, customResponse, linkUrl]);

  const handleDismissSpike = useCallback(() => {
    setSpikeAlert({ visible: false, message: "" });
  }, []);

  const handleHideCluster = useCallback(async (clusterId: string) => {
    try {
      await hideCluster(clusterId);
      setClusters((prev) =>
        prev.map((c) => (c.id === clusterId ? { ...c, status: "hidden" } : c))
      );
    } catch {
      // silently fail
    }
  }, []);

  const handleRestoreCluster = useCallback(async (clusterId: string) => {
    try {
      await restoreCluster(clusterId);
      setClusters((prev) =>
        prev.map((c) => (c.id === clusterId ? { ...c, status: "pending" } : c))
      );
    } catch {
      // silently fail
    }
  }, []);

  const handleGenerateReport = useCallback(async () => {
    if (!sessionId) return;
    setReportLoading(true);
    try {
      const data = await generateReport(sessionId);
      setReport(data);
      setShowReport(true);
      setSessionEnded(true);
    } catch {
      // keep going on error
    } finally {
      setReportLoading(false);
    }
  }, [sessionId]);

  // Split clusters into visible and hidden, sort by question_count descending
  const visibleClusters = [...clusters]
    .filter((c) => c.status !== "hidden")
    .sort((a, b) => b.question_count - a.question_count);
  const hiddenClusters = [...clusters]
    .filter((c) => c.status === "hidden")
    .sort((a, b) => b.question_count - a.question_count);

  return (
    <main className="min-h-screen p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Session Ended Banner */}
        {sessionEnded && (
          <div className="rounded-lg border border-red-300 bg-red-50 dark:border-red-800 dark:bg-red-950 px-4 py-3 flex items-center gap-3">
            <StopCircle className="h-5 w-5 text-red-600 dark:text-red-400 shrink-0" />
            <div>
              <p className="font-semibold text-red-700 dark:text-red-300">Session Ended</p>
              <p className="text-sm text-red-600 dark:text-red-400">
                This session has been closed. The report is available below.
              </p>
            </div>
          </div>
        )}

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold">Host Dashboard</h1>
            <p className="text-muted-foreground text-base">Session ID: {sessionId}</p>
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
          <Card className="border-2 border-primary/30">
            <CardHeader>
              <CardTitle className="flex items-center justify-between text-lg">
                Confusion Index
                <Badge variant="outline">Live</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="flex justify-center">
              <ConfusionGauge value={confusionIndex} threshold={threshold} />
            </CardContent>
          </Card>

          {/* Participants */}
          <Card className="border-2 border-primary/30">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Users className="h-5 w-5" />
                Participants
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-7xl font-bold text-center py-8">
                <AnimatedCounter value={participantCount} />
              </div>
              <p className="text-center text-base text-muted-foreground">
                Participants connected
              </p>
            </CardContent>
          </Card>

          {/* Questions */}
          <Card className="border-2 border-primary/30">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <MessageSquare className="h-5 w-5" />
                Questions
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-7xl font-bold text-center py-8">
                <AnimatedCounter value={questionCount} />
              </div>
              <p className="text-center text-base text-muted-foreground">
                Questions submitted
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Confusion Timeline */}
        <Card>
          <CardHeader>
            <CardTitle>Confusion Timeline</CardTitle>
          </CardHeader>
          <CardContent>
            {timeline.length === 0 ? (
              <p className="text-muted-foreground text-center py-12">
                No check-in data yet
              </p>
            ) : (
              <ConfusionChart
                data={timeline.map((entry) => ({
                  slide: entry.slide,
                  confusion_pct: entry.confusion_pct,
                  responses: entry.responses,
                }))}
                threshold={threshold}
              />
            )}
          </CardContent>
        </Card>

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
              <Button onClick={handleTriggerCheckin} disabled={checkinInProgress || sessionEnded}>
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
              disabled={clusterLoading || sessionEnded}
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
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Question Clusters</h2>
            {hiddenClusters.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowHidden((prev) => !prev)}
                className="text-muted-foreground"
              >
                {showHidden ? (
                  <>
                    <EyeOff className="h-4 w-4 mr-1" />
                    Hide Hidden ({hiddenClusters.length})
                  </>
                ) : (
                  <>
                    <Eye className="h-4 w-4 mr-1" />
                    Show Hidden ({hiddenClusters.length})
                  </>
                )}
              </Button>
            )}
          </div>
          {visibleClusters.length === 0 && hiddenClusters.length === 0 ? (
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
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {visibleClusters.map((cluster, index) => (
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
                      <p className="text-sm text-muted-foreground">
                        {cluster.summary || cluster.representative_question}
                      </p>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          <span>{cluster.question_count} questions</span>
                          <span className="flex items-center gap-1">
                            <ArrowUpCircle className="h-3.5 w-3.5" />
                            {cluster.upvotes}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          {cluster.status === "pending" && (
                            <>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleHideCluster(cluster.id)}
                                className="text-muted-foreground h-8 px-2"
                              >
                                <EyeOff className="h-3.5 w-3.5 mr-1" />
                                Hide
                              </Button>
                              <Button
                                size="sm"
                                onClick={() => handleAddressCluster(cluster)}
                              >
                                Address
                              </Button>
                            </>
                          )}
                          {cluster.status === "addressed" && (
                            <span className="text-xs text-green-600 font-medium">
                              Addressed
                            </span>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              {/* Hidden Clusters Section */}
              {showHidden && hiddenClusters.length > 0 && (
                <div className="mt-6">
                  <h3 className="text-sm font-medium text-muted-foreground mb-3">
                    Hidden Clusters
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {hiddenClusters.map((cluster) => (
                      <Card
                        key={cluster.id}
                        className="opacity-50 border-dashed"
                      >
                        <CardHeader>
                          <CardTitle className="flex items-center justify-between text-base">
                            <span className="flex items-center gap-2">
                              {cluster.label}
                            </span>
                            <Badge variant="outline" className="text-muted-foreground">
                              Hidden
                            </Badge>
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
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleRestoreCluster(cluster.id)}
                            >
                              <RotateCcw className="h-3.5 w-3.5 mr-1" />
                              Restore
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* End Session & Generate Report */}
        <Card>
          <CardContent className="flex items-center justify-between pt-4">
            <div>
              <p className="font-medium">End Session</p>
              <p className="text-sm text-muted-foreground">
                Generate a comprehensive report and close the session
              </p>
            </div>
            <Button
              variant="destructive"
              onClick={handleGenerateReport}
              disabled={reportLoading || sessionEnded}
            >
              {reportLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Generating Report...
                </>
              ) : sessionEnded ? (
                <>
                  <StopCircle className="h-4 w-4" />
                  Session Ended
                </>
              ) : (
                <>
                  <StopCircle className="h-4 w-4" />
                  End Session &amp; Generate Report
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Report Modal */}
        <Dialog
          open={showReport}
          onOpenChange={(open) => {
            if (!open) setShowReport(false);
          }}
        >
          <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Session Report</DialogTitle>
              <DialogDescription>
                End-of-session analytics and summary
              </DialogDescription>
            </DialogHeader>
            {report && (
              <ReportView report={report} sessionTitle={sessionTitle} sessionId={sessionId} />
            )}
            <DialogFooter showCloseButton />
          </DialogContent>
        </Dialog>

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

            <div className="space-y-4">
              <p className="text-sm font-medium">How do you want to respond?</p>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { value: "explained_now", label: "💡 Answer Now", desc: "AI drafts a response you can edit" },
                  { value: "send_link", label: "🔗 Send Link", desc: "Share a video, article, or resource" },
                  { value: "flagged_next_class", label: "📌 Mark for Later", desc: "Address next session" },
                  { value: "text_response", label: "✏️ Type Response", desc: "Write your own answer" },
                ].map((option) => (
                  <button
                    key={option.value}
                    onClick={() => {
                      setAddressResponseType(option.value);
                      if (option.value !== "explained_now") setAiDraft("");
                    }}
                    className={`text-left p-3 rounded-lg border transition-colors ${
                      addressResponseType === option.value
                        ? "border-primary bg-primary/5"
                        : "border-muted hover:border-muted-foreground/30"
                    }`}
                  >
                    <p className="text-sm font-medium">{option.label}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{option.desc}</p>
                  </button>
                ))}
              </div>

              {/* Answer Now — AI Draft */}
              {addressResponseType === "explained_now" && (
                <div className="space-y-2">
                  {!aiDraft && !aiDraftLoading && (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={handleGenerateAiDraft}
                      className="w-full"
                    >
                      <Sparkles className="h-4 w-4 mr-1" />
                      Generate AI Suggestion
                    </Button>
                  )}
                  {aiDraftLoading && (
                    <div className="flex items-center justify-center gap-2 py-4 text-sm text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      AI is drafting a response...
                    </div>
                  )}
                  {aiDraft && !aiDraftLoading && (
                    <>
                      <p className="text-xs text-muted-foreground">AI suggestion — edit before sending:</p>
                      <textarea
                        className="w-full min-h-[120px] rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        value={customResponse}
                        onChange={(e) => setCustomResponse(e.target.value)}
                        placeholder="Edit the AI suggestion or write your own..."
                      />
                    </>
                  )}
                </div>
              )}

              {/* Send Link */}
              {addressResponseType === "send_link" && (
                <div className="space-y-2">
                  <Input
                    placeholder="Paste URL (YouTube, article, docs...)"
                    value={linkUrl}
                    onChange={(e) => setLinkUrl(e.target.value)}
                  />
                  <Input
                    placeholder="Optional note for students..."
                    value={customResponse}
                    onChange={(e) => setCustomResponse(e.target.value)}
                  />
                </div>
              )}

              {/* Type Response */}
              {addressResponseType === "text_response" && (
                <textarea
                  className="w-full min-h-[100px] rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  placeholder="Type your response to students..."
                  value={customResponse}
                  onChange={(e) => setCustomResponse(e.target.value)}
                />
              )}

              {/* Mark for Later — just a confirmation message */}
              {addressResponseType === "flagged_next_class" && (
                <p className="text-sm text-muted-foreground bg-muted rounded-lg p-3">
                  This cluster will be flagged and included in the session report as a topic to revisit next class.
                </p>
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
                ) : addressResponseType === "flagged_next_class" ? (
                  "Flag for Later"
                ) : (
                  "Send to Students"
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
