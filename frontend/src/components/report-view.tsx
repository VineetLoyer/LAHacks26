"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ReportData } from "@/lib/api";
import { getFeedbackSummary } from "@/lib/api";
import {
  Users,
  MessageSquare,
  CheckCircle2,
  TrendingUp,
  AlertTriangle,
  Flag,
  Sparkles,
  Download,
  Star,
  RefreshCw,
  Loader2,
} from "lucide-react";

interface FeedbackData {
  average_rating: number;
  total_count: number;
  distribution: Record<string, number>;
  useful_comments: string[];
  summary_bullets: string[];
  raw_comment_count: number;
}

interface ReportViewProps {
  report: ReportData;
  sessionTitle?: string;
  sessionId?: string;
}

export function ReportView({ report, sessionTitle, sessionId }: ReportViewProps) {
  const [liveFeedback, setLiveFeedback] = useState<FeedbackData | null>(null);
  const [feedbackLoading, setFeedbackLoading] = useState(false);

  const fetchFeedback = useCallback(async () => {
    if (!sessionId) return;
    setFeedbackLoading(true);
    try {
      const data = await getFeedbackSummary(sessionId);
      setLiveFeedback(data);
    } catch {
      // Non-blocking — keep showing whatever we have
    } finally {
      setFeedbackLoading(false);
    }
  }, [sessionId]);

  // Fetch live feedback on mount
  useEffect(() => {
    fetchFeedback();
  }, [fetchFeedback]);

  const resolutionRate =
    report.clusters_total > 0
      ? Math.round((report.clusters_addressed / report.clusters_total) * 100)
      : 0;

  // Use live feedback if available, fall back to report's feedback_summary
  const feedback: FeedbackData | null = liveFeedback
    ? liveFeedback
    : report.feedback_summary && report.feedback_summary.total_count > 0
      ? {
          average_rating: report.feedback_summary.average_rating,
          total_count: report.feedback_summary.total_count,
          distribution: {},
          useful_comments: [],
          summary_bullets: [],
          raw_comment_count: 0,
        }
      : null;

  const hasFeedback = feedback !== null && feedback.total_count > 0;

  return (
    <div className="space-y-6" id="report-print-content">
      {/* Header */}
      <div className="text-center space-y-1">
        <h2 className="text-2xl font-bold">Session Report</h2>
        {sessionTitle && (
          <p className="text-muted-foreground">{sessionTitle}</p>
        )}
        <Button
          variant="outline"
          size="sm"
          className="mt-2"
          onClick={() => {
            // Build clean HTML with inline styles (no oklch colors)
            const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Session Report</title>
<style>
body{font-family:system-ui,sans-serif;max-width:800px;margin:2rem auto;padding:0 1rem;color:#1a1a1a}
h2{text-align:center;margin-bottom:.25rem}
.sub{text-align:center;color:#666;margin-bottom:1.5rem}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.5rem}
.card{border:1px solid #e5e5e5;border-radius:8px;padding:1rem}
.val{font-size:1.5rem;font-weight:700}.lbl{font-size:.75rem;color:#666}
.sec{border:1px solid #e5e5e5;border-radius:8px;padding:1rem;margin-bottom:1rem}
.st{font-weight:600;margin-bottom:.5rem}
.sp{background:#fef2f2;padding:.5rem;border-radius:4px;margin-bottom:.5rem}
.badge{background:#f3f4f6;padding:2px 8px;border-radius:4px;font-size:.8rem}
.fl{padding:.25rem 0}.dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:#f59e0b;margin-right:8px}
.sum{white-space:pre-line;color:#555;line-height:1.6}
</style></head><body>
<h2>Session Report</h2>
<p class="sub">${sessionTitle || ""}</p>
<div class="grid">
<div class="card"><div class="val">${report.total_participants}</div><div class="lbl">Total Participants</div></div>
<div class="card"><div class="val">${report.total_questions}</div><div class="lbl">Total Questions</div></div>
<div class="card"><div class="val">${report.clusters_addressed} of ${report.clusters_total}</div><div class="lbl">Clusters Addressed</div></div>
<div class="card"><div class="val">${resolutionRate}%</div><div class="lbl">Resolution Rate</div></div>
</div>
${report.confusion_spikes.length > 0 ? `<div class="sec"><div class="st">⚠️ Confusion Spikes</div>${report.confusion_spikes.map((s: { slide: number; confusion_pct: number; description?: string }) => `<div class="sp"><span class="badge">Slide ${s.slide}</span> <strong>${s.confusion_pct}%</strong>${s.description ? `<div style="font-size:.8rem;color:#666;margin-top:2px">${s.description}</div>` : ""}</div>`).join("")}</div>` : ""}
${report.flagged_for_next_lecture.length > 0 ? `<div class="sec"><div class="st">🚩 Flagged for Next Session</div>${report.flagged_for_next_lecture.map((t: string) => `<div class="fl"><span class="dot"></span>${t}</div>`).join("")}</div>` : ""}
<div class="sec"><div class="st">✨ AI Summary</div><div class="sum">${report.summary}</div></div>
</body></html>`;
            // Use hidden iframe to print — avoids popup blockers and dialog issues
            let iframe = document.getElementById("report-print-frame") as HTMLIFrameElement;
            if (!iframe) {
              iframe = document.createElement("iframe");
              iframe.id = "report-print-frame";
              iframe.style.position = "fixed";
              iframe.style.right = "0";
              iframe.style.bottom = "0";
              iframe.style.width = "0";
              iframe.style.height = "0";
              iframe.style.border = "none";
              document.body.appendChild(iframe);
            }
            const doc = iframe.contentDocument || iframe.contentWindow?.document;
            if (!doc) return;
            doc.open();
            doc.write(html);
            doc.close();
            setTimeout(() => {
              iframe.contentWindow?.print();
            }, 300);
          }}
        >
          <Download className="h-4 w-4 mr-1" />
          Download Report
        </Button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-4">
        <Card size="sm">
          <CardContent className="flex items-center gap-3 pt-3">
            <div className="rounded-lg bg-blue-500/10 p-2">
              <Users className="h-5 w-5 text-blue-500" />
            </div>
            <div>
              <p className="text-2xl font-bold">{report.total_participants}</p>
              <p className="text-xs text-muted-foreground">Total Participants</p>
            </div>
          </CardContent>
        </Card>

        <Card size="sm">
          <CardContent className="flex items-center gap-3 pt-3">
            <div className="rounded-lg bg-purple-500/10 p-2">
              <MessageSquare className="h-5 w-5 text-purple-500" />
            </div>
            <div>
              <p className="text-2xl font-bold">{report.total_questions}</p>
              <p className="text-xs text-muted-foreground">Total Questions</p>
            </div>
          </CardContent>
        </Card>

        <Card size="sm">
          <CardContent className="flex items-center gap-3 pt-3">
            <div className="rounded-lg bg-green-500/10 p-2">
              <CheckCircle2 className="h-5 w-5 text-green-500" />
            </div>
            <div>
              <p className="text-2xl font-bold">
                {report.clusters_addressed}{" "}
                <span className="text-sm font-normal text-muted-foreground">
                  of {report.clusters_total}
                </span>
              </p>
              <p className="text-xs text-muted-foreground">Clusters Addressed</p>
            </div>
          </CardContent>
        </Card>

        <Card size="sm">
          <CardContent className="flex items-center gap-3 pt-3">
            <div className="rounded-lg bg-amber-500/10 p-2">
              <TrendingUp className="h-5 w-5 text-amber-500" />
            </div>
            <div>
              <p className="text-2xl font-bold">{resolutionRate}%</p>
              <p className="text-xs text-muted-foreground">Resolution Rate</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Confusion Spikes */}
      {report.confusion_spikes.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertTriangle className="h-4 w-4 text-red-500" />
              Confusion Spikes
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {report.confusion_spikes.map((spike) => (
              <div
                key={spike.slide}
                className="flex items-start gap-3 rounded-lg bg-red-500/5 p-3"
              >
                <Badge variant="secondary" className="shrink-0">
                  Slide {spike.slide}
                </Badge>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">
                    {spike.confusion_pct}% confused
                  </p>
                  {spike.description && (
                    <p className="text-xs text-muted-foreground mt-0.5 truncate">
                      {spike.description}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Flagged for Next Session */}
      {report.flagged_for_next_lecture.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Flag className="h-4 w-4 text-amber-500" />
              Flagged for Next Session
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {report.flagged_for_next_lecture.map((topic) => (
                <li
                  key={topic}
                  className="flex items-center gap-2 text-sm"
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-500 shrink-0" />
                  {topic}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* AI Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Sparkles className="h-4 w-4 text-purple-500" />
            AI Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm leading-relaxed whitespace-pre-line text-muted-foreground">
            {report.summary}
          </div>
        </CardContent>
      </Card>

      {/* Participant Feedback — Live */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between text-base">
            <span className="flex items-center gap-2">
              <Star className="h-4 w-4 text-yellow-500" />
              Participant Feedback
            </span>
            {sessionId && (
              <Button
                variant="ghost"
                size="sm"
                onClick={fetchFeedback}
                disabled={feedbackLoading}
                className="h-8 px-2"
              >
                {feedbackLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
                <span className="ml-1 text-xs">Refresh</span>
              </Button>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {!hasFeedback ? (
            <p className="text-sm text-muted-foreground">
              No feedback submitted yet — participants can rate the session after it ends.
            </p>
          ) : (
            <>
              {/* Star rating */}
              <div className="flex items-center gap-3">
                <span className="text-2xl font-bold">
                  {feedback.average_rating}
                </span>
                <span
                  className="text-lg tracking-wide"
                  aria-label={`${feedback.average_rating} out of 5 stars`}
                >
                  {Array.from({ length: 5 }, (_, i) =>
                    i < Math.round(feedback.average_rating) ? "★" : "☆"
                  ).join("")}
                </span>
                <span className="text-sm text-muted-foreground">/ 5</span>
              </div>
              <p className="text-sm text-muted-foreground">
                Based on {feedback.total_count} participant
                {feedback.total_count !== 1 ? "s" : ""}
              </p>

              {/* AI Insights (summary bullets) */}
              {feedback.summary_bullets && feedback.summary_bullets.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium flex items-center gap-1.5">
                    <Sparkles className="h-3.5 w-3.5 text-purple-500" />
                    AI Insights
                  </p>
                  <ul className="space-y-1.5">
                    {feedback.summary_bullets.map((bullet, i) => (
                      <li
                        key={i}
                        className="flex items-start gap-2 text-sm text-muted-foreground"
                      >
                        <span className="h-1.5 w-1.5 rounded-full bg-purple-500 shrink-0 mt-1.5" />
                        {bullet}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Useful participant comments */}
              {feedback.useful_comments && feedback.useful_comments.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium">Participant Comments</p>
                  <div className="space-y-2">
                    {feedback.useful_comments.map((comment, i) => (
                      <div
                        key={i}
                        className="rounded-lg bg-muted/50 px-3 py-2 text-sm text-muted-foreground italic"
                      >
                        &ldquo;{comment}&rdquo;
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}