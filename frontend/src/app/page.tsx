"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Activity,
  BrainCircuit,
  ShieldCheck,
  BarChart3,
  ArrowRight,
  Fingerprint,
} from "lucide-react";

const features = [
  {
    icon: Activity,
    emoji: "🎯",
    title: "Real-Time Confusion Detection",
    description:
      "AI monitors student confusion and alerts professors to spikes as they happen.",
  },
  {
    icon: BrainCircuit,
    emoji: "🤖",
    title: "AI Question Clustering",
    description:
      "Gemini groups similar questions so professors address topics, not individual messages.",
  },
  {
    icon: ShieldCheck,
    emoji: "🔒",
    title: "Proof of Human",
    description:
      "World ID verification ensures every participant is a real person.",
  },
  {
    icon: BarChart3,
    emoji: "📊",
    title: "Session Analytics",
    description:
      "Post-session reports with AI insights and student feedback.",
  },
];

const techStack = [
  "Fetch.ai Agentverse",
  "Google Gemini",
  "World ID",
  "MongoDB Atlas",
  "ElevenLabs",
];

export default function Home() {
  return (
    <main className="flex flex-col items-center min-h-screen">
      {/* Hero Section */}
      <section className="flex flex-col items-center justify-center flex-1 w-full px-6 pt-24 pb-16">
        <div className="text-center max-w-3xl mx-auto">
          <h1 className="text-6xl sm:text-7xl font-bold tracking-tight mb-3">
            Ask<span className="text-primary">Safe</span>
          </h1>
          <p className="text-lg sm:text-xl text-muted-foreground font-medium mb-1">
            Anonymous Q&amp;A for live lectures — powered by AI
          </p>
          <p className="text-base text-muted-foreground/70 mb-10 max-w-xl mx-auto">
            Real-time confusion detection, question clustering, and
            proof-of-human verification — so every voice is heard safely.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/professor">
              <Button size="lg" className="text-base px-8 gap-2 w-full sm:w-auto bg-primary hover:bg-primary/90">
                Start a Session
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link href="/join">
              <Button
                size="lg"
                variant="outline"
                className="text-base px-8 w-full sm:w-auto"
              >
                Join a Session
              </Button>
            </Link>
          </div>

          {/* Trust badge */}
          <div className="mt-6 flex items-center justify-center gap-1.5 text-xs text-muted-foreground/70">
            <Fingerprint className="h-3.5 w-3.5" />
            <span>Verified by World ID · Proof of Human</span>
          </div>
        </div>
      </section>

      {/* Feature Cards */}
      <section className="w-full max-w-5xl mx-auto px-6 pb-16">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {features.map((f) => (
            <Card
              key={f.title}
              className="border border-border/60 shadow-sm hover:shadow-md transition-shadow"
            >
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  <span className="text-lg">{f.emoji}</span>
                  {f.title}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {f.description}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* Powered By */}
      <footer className="w-full border-t py-8 px-6">
        <div className="max-w-5xl mx-auto text-center">
          <p className="text-xs text-muted-foreground/60 uppercase tracking-widest mb-3">
            Powered by
          </p>
          <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
            {techStack.map((tech) => (
              <span
                key={tech}
                className="text-sm text-muted-foreground font-medium"
              >
                {tech}
              </span>
            ))}
          </div>
        </div>
      </footer>
    </main>
  );
}
