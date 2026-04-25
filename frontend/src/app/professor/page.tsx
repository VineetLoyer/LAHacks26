"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";
import { createSession, createSessionWithFile } from "@/lib/api";
import { Upload, X, FileText } from "lucide-react";

const ACCEPTED_TYPES = ".pdf,.docx,.pptx";
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50 MB

export default function ProfessorPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [anonymousMode, setAnonymousMode] = useState(true);
  const [demoMode, setDemoMode] = useState(false);
  const [threshold, setThreshold] = useState([60]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    if (file && file.size > MAX_FILE_SIZE) {
      setError("File exceeds 50MB limit");
      setSelectedFile(null);
      return;
    }
    setError("");
    setSelectedFile(file);
  }

  function handleRemoveFile() {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  async function handleCreate() {
    if (!title.trim()) {
      setError("Please enter a session title");
      return;
    }
    setLoading(true);
    setError("");
    setUploadStatus("");

    try {
      if (selectedFile) {
        // Use multipart form data endpoint
        setUploadStatus("Uploading and parsing slides...");
        const formData = new FormData();
        formData.append("title", title.trim());
        formData.append("anonymous_mode", String(anonymousMode));
        formData.append("confusion_threshold", String(threshold[0]));
        formData.append("demo_mode", String(demoMode));
        formData.append("file", selectedFile);

        const session = await createSessionWithFile(formData);
        router.push(
          `/professor/dashboard?id=${session.id}&code=${session.code}`
        );
      } else {
        // Use existing JSON endpoint (no file)
        const session = await createSession({
          title: title.trim(),
          anonymous_mode: anonymousMode,
          confusion_threshold: threshold[0],
          demo_mode: demoMode,
        });
        router.push(
          `/professor/dashboard?id=${session.id}&code=${session.code}`
        );
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create session");
      setUploadStatus("");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-8">
      {/* Branding */}
      <Link href="/" className="mb-8 text-center group">
        <h2 className="text-3xl font-bold tracking-tight">
          Ask<span className="text-primary">Safe</span>
        </h2>
        <p className="text-xs text-muted-foreground/60 group-hover:text-muted-foreground transition-colors">
          Anonymous Q&amp;A for Live Lectures
        </p>
      </Link>

      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle className="text-2xl">Create a Session</CardTitle>
          <p className="text-sm text-muted-foreground">
            Set up a live Q&amp;A session for your lecture
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Session Title */}
          <div>
            <label className="text-sm font-medium mb-2 block">
              Session Title
            </label>
            <Input
              placeholder="e.g. CS101 — Recursion"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          {/* Confusion Threshold */}
          <div>
            <label className="text-sm font-medium mb-2 block">
              Confusion Alert Threshold: {threshold[0]}%
            </label>
            <Slider
              value={threshold}
              onValueChange={(val) =>
                setThreshold(Array.isArray(val) ? val : [val])
              }
              min={10}
              max={100}
              step={5}
            />
            <p className="text-xs text-muted-foreground mt-1">
              Alert fires when confusion exceeds this percentage
            </p>
          </div>

          {/* File Upload */}
          <div>
            <label className="text-sm font-medium mb-2 block">
              Lecture Material{" "}
              <span className="text-muted-foreground font-normal">
                (optional)
              </span>
            </label>
            {!selectedFile ? (
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="w-full border-2 border-dashed border-border/80 rounded-lg p-6 text-center hover:border-primary/40 hover:bg-muted/30 transition-colors cursor-pointer group"
              >
                <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground/50 group-hover:text-primary/60 transition-colors" />
                <p className="text-sm font-medium text-muted-foreground group-hover:text-foreground transition-colors">
                  Click to upload slides
                </p>
                <p className="text-xs text-muted-foreground/60 mt-1">
                  PDF, DOCX, or PPTX — max 50 MB
                </p>
              </button>
            ) : (
              <div className="flex items-center gap-3 border border-border/80 rounded-lg px-4 py-3 bg-muted/30">
                <FileText className="h-5 w-5 text-primary shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">
                    {selectedFile.name}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {(selectedFile.size / 1024 / 1024).toFixed(1)} MB
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleRemoveFile}
                  className="text-muted-foreground hover:text-red-500 transition-colors"
                  aria-label="Remove selected file"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_TYPES}
              onChange={handleFileChange}
              className="hidden"
              aria-label="Upload lecture slides"
            />
            <p className="text-xs text-muted-foreground mt-1.5">
              Slide content helps AI generate better explanations.
            </p>
          </div>

          {/* Demo Mode Toggle */}
          <div className="rounded-lg border border-border/80 p-4">
            <div className="flex items-start gap-3">
              <input
                type="checkbox"
                id="demo"
                checked={demoMode}
                onChange={(e) => setDemoMode(e.target.checked)}
                className="h-4 w-4 mt-0.5 accent-primary"
              />
              <div className="flex-1">
                <label
                  htmlFor="demo"
                  className="text-sm font-medium flex items-center gap-2 cursor-pointer"
                >
                  Demo Mode
                  <Badge variant="secondary">Hackathon</Badge>
                </label>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Skips World ID verification so judges can join instantly.
                  Simulated confusion data is generated automatically.
                </p>
              </div>
            </div>
          </div>

          {/* Anonymous Mode */}
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="anon"
              checked={anonymousMode}
              onChange={(e) => setAnonymousMode(e.target.checked)}
              className="h-4 w-4 accent-primary"
            />
            <label htmlFor="anon" className="text-sm cursor-pointer">
              Anonymous Mode{" "}
              <span className="text-muted-foreground">
                (no participant data stored)
              </span>
            </label>
          </div>

          {error && <p className="text-sm text-red-500">{error}</p>}
          {uploadStatus && !error && (
            <p className="text-sm text-primary animate-pulse">{uploadStatus}</p>
          )}

          <Button
            onClick={handleCreate}
            disabled={loading}
            className="w-full bg-primary hover:bg-primary/90"
            size="lg"
          >
            {loading
              ? selectedFile
                ? "Uploading & Creating..."
                : "Creating..."
              : "Create Session"}
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}
