"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function Home() {
  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-8">
      {/* Hero */}
      <div className="text-center max-w-3xl mx-auto mb-16">
        <h1 className="text-5xl font-bold tracking-tight mb-4">
          Ask<span className="text-emerald-500">Safe</span>
        </h1>
        <p className="text-xl text-muted-foreground mb-2">
          Transform silent anxiety into engaged, data-driven learning.
        </p>
        <p className="text-muted-foreground mb-8">
          Anonymous Q&amp;A with real-time AI confusion detection &amp;
          post-lecture insights.
        </p>
        <div className="flex gap-4 justify-center">
          <Link href="/professor">
            <Button size="lg" className="text-lg px-8">
              I&apos;m a Professor
            </Button>
          </Link>
          <Link href="/join">
            <Button size="lg" variant="outline" className="text-lg px-8">
              Join a Session
            </Button>
          </Link>
        </div>
      </div>

      {/* Feature Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl w-full">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              🛡️ Anonymous &amp; Safe
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">
              Students ask questions without fear. World ID verifies
              you&apos;re human — not who you are.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              🧠 AI-Powered Clustering
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">
              Instead of 1000 similar questions, AI groups them into
              actionable topic clusters professors can address.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              📊 Real-Time Insights
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">
              Live confusion index, spike alerts, and post-session
              reports with confusion timelines.
            </p>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
