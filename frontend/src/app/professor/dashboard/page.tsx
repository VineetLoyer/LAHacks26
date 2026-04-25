"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

function DashboardContent() {
  const params = useSearchParams();
  const sessionId = params.get("id") || "";
  const sessionCode = params.get("code") || "";

  return (
    <main className="min-h-screen p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">Professor Dashboard</h1>
            <p className="text-muted-foreground">Session ID: {sessionId}</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-muted-foreground">Session Code</p>
            <p className="text-4xl font-mono font-bold tracking-widest">
              {sessionCode}
            </p>
            <p className="text-xs text-muted-foreground">
              Share this code with students
            </p>
          </div>
        </div>

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Confusion Index */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Confusion Index
                <Badge variant="outline">Live</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-6xl font-bold text-center py-8">
                0<span className="text-2xl text-muted-foreground">%</span>
              </div>
              <p className="text-center text-sm text-muted-foreground">
                Waiting for check-in responses...
              </p>
            </CardContent>
          </Card>

          {/* Participants */}
          <Card>
            <CardHeader>
              <CardTitle>Participants</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-6xl font-bold text-center py-8">0</div>
              <p className="text-center text-sm text-muted-foreground">
                Students connected
              </p>
            </CardContent>
          </Card>

          {/* Questions */}
          <Card>
            <CardHeader>
              <CardTitle>Questions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-6xl font-bold text-center py-8">0</div>
              <p className="text-center text-sm text-muted-foreground">
                Questions submitted
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Question Clusters placeholder */}
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Question Clusters</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground text-center py-12">
              Clusters will appear here after students submit questions and you
              trigger AI clustering.
            </p>
          </CardContent>
        </Card>
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
