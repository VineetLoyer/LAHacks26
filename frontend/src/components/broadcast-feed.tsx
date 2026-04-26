"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export interface Broadcast {
  cluster_id: string;
  label: string;
  ai_explanation: string;
  professor_response: string | null;
  response_type: string;
  timestamp: string;
}

function responseTypeBadge(type: string) {
  switch (type) {
    case "explained_now":
      return <Badge variant="default">Explained</Badge>;
    case "flagged_next_class":
      return <Badge variant="secondary">Flagged for Next Session</Badge>;
    case "text_response":
      return <Badge variant="outline">Custom Response</Badge>;
    case "send_link":
      return <Badge variant="outline">Resource Shared</Badge>;
    default:
      return <Badge variant="outline">{type}</Badge>;
  }
}

function formatTime(iso: string) {
  try {
    return new Date(iso).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

export function BroadcastFeed({ broadcasts }: { broadcasts: Broadcast[] }) {
  if (broadcasts.length === 0) return null;

  return (
    <div className="mb-6 space-y-3">
      <h2 className="text-lg font-semibold">Responses from Host</h2>
      {broadcasts.map((b, i) => (
        <Card
          key={`${b.cluster_id}-${i}`}
          className="broadcast-slide-in border-blue-400/50"
          style={{ animationDelay: `${i * 60}ms` }}
        >
          <CardHeader className="pb-1">
            <div className="flex items-center justify-between gap-2">
              <CardTitle className="text-sm">{b.label}</CardTitle>
              {responseTypeBadge(b.response_type)}
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {b.professor_response || b.ai_explanation}
            </p>
            {b.professor_response && b.ai_explanation && b.professor_response !== b.ai_explanation && (
              <p className="mt-2 text-xs text-muted-foreground italic">
                AI draft was edited by instructor
              </p>
            )}
            <p className="mt-2 text-xs text-muted-foreground">
              {formatTime(b.timestamp)}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
