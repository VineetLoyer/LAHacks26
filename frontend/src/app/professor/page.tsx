"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { createSession, createSessionWithFile } from "@/lib/api";

const ACCEPTED_TYPES = ".pdf,.docx,.pptx";
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50 MB

export default function ProfessorPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [anonymousMode, setAnonymousMode] = useState(true);
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
        formData.append("demo_mode", "false");
        formData.append("file", selectedFile);

        const session = await createSessionWithFile(formData);
        router.push(`/professor/dashboard?id=${session.id}&code=${session.code}`);
      } else {
        // Use existing JSON endpoint (no file)
        const session = await createSession({
          title: title.trim(),
          anonymous_mode: anonymousMode,
          confusion_threshold: threshold[0],
        });
        router.push(`/professor/dashboard?id=${session.id}&code=${session.code}`);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create session");
      setUploadStatus("");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex items-center justify-center min-h-screen p-8">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle className="text-2xl">Create a Session</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
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

          <div>
            <label className="text-sm font-medium mb-2 block">
              Confusion Alert Threshold: {threshold[0]}%
            </label>
            <Slider
              value={threshold}
              onValueChange={(val) => setThreshold(Array.isArray(val) ? val : [val])}
              min={10}
              max={100}
              step={5}
            />
            <p className="text-xs text-muted-foreground mt-1">
              Alert fires when confusion exceeds this percentage
            </p>
          </div>

          <div>
            <label className="text-sm font-medium mb-2 block">
              Lecture Material (optional)
            </label>
            <div className="space-y-2">
              <Input
                ref={fileInputRef}
                type="file"
                accept={ACCEPTED_TYPES}
                onChange={handleFileChange}
                className="cursor-pointer"
                aria-label="Upload lecture slides"
              />
              <p className="text-xs text-muted-foreground">
                PDF, DOCX, or PPTX — max 50MB. Slide content helps AI generate better explanations.
              </p>
              {selectedFile && (
                <div className="flex items-center gap-2 text-sm bg-muted/50 rounded-md px-3 py-2">
                  <span className="truncate flex-1">{selectedFile.name}</span>
                  <span className="text-muted-foreground text-xs whitespace-nowrap">
                    {(selectedFile.size / 1024 / 1024).toFixed(1)} MB
                  </span>
                  <button
                    type="button"
                    onClick={handleRemoveFile}
                    className="text-red-500 hover:text-red-700 text-xs font-medium ml-1"
                    aria-label="Remove selected file"
                  >
                    Remove
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="anon"
              checked={anonymousMode}
              onChange={(e) => setAnonymousMode(e.target.checked)}
              className="h-4 w-4"
            />
            <label htmlFor="anon" className="text-sm">
              Anonymous Mode (no participant data stored)
            </label>
          </div>

          {error && <p className="text-sm text-red-500">{error}</p>}
          {uploadStatus && !error && (
            <p className="text-sm text-blue-500 animate-pulse">{uploadStatus}</p>
          )}

          <Button
            onClick={handleCreate}
            disabled={loading}
            className="w-full"
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
