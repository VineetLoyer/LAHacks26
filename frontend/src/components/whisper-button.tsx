"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Mic, MicOff, Loader2 } from "lucide-react";

interface WhisperButtonProps {
  onTranscript: (text: string) => void;
  disabled?: boolean;
}

type RecordingState = "idle" | "recording" | "transcribing";

// Check if Web Speech API is available
function hasSpeechRecognition(): boolean {
  if (typeof window === "undefined") return false;
  return !!(
    (window as unknown as Record<string, unknown>).SpeechRecognition ||
    (window as unknown as Record<string, unknown>).webkitSpeechRecognition
  );
}

// ElevenLabs Scribe API transcription
async function transcribeWithElevenLabs(audioBlob: Blob): Promise<string> {
  const apiKey = process.env.NEXT_PUBLIC_ELEVENLABS_API_KEY;
  if (!apiKey) throw new Error("No ElevenLabs API key");

  const formData = new FormData();
  formData.append("file", audioBlob, "recording.webm");
  formData.append("model_id", "scribe_v2");

  const resp = await fetch(
    "https://api.elevenlabs.io/v1/speech-to-text",
    {
      method: "POST",
      headers: { "xi-api-key": apiKey },
      body: formData,
    }
  );

  if (!resp.ok) throw new Error(`ElevenLabs error: ${resp.status}`);
  const data = await resp.json();
  return data.text || "";
}

export function WhisperButton({ onTranscript, disabled }: WhisperButtonProps) {
  const [state, setState] = useState<RecordingState>("idle");
  const [supported, setSupported] = useState(true);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);

  const hasElevenLabsKey = !!process.env.NEXT_PUBLIC_ELEVENLABS_API_KEY;

  // Check browser support on mount
  useEffect(() => {
    const canRecord =
      typeof navigator !== "undefined" &&
      !!navigator.mediaDevices?.getUserMedia;
    const canSpeech = hasSpeechRecognition();
    setSupported(canRecord || canSpeech);
  }, []);

  // Stop recording and transcribe via ElevenLabs
  const stopMediaRecorder = useCallback(() => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }
  }, []);

  // Start recording with MediaRecorder (for ElevenLabs path)
  const startMediaRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus"
          : "audio/webm",
      });
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        // Stop all tracks to release the microphone
        stream.getTracks().forEach((t) => t.stop());

        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        if (blob.size === 0) {
          setState("idle");
          return;
        }

        setState("transcribing");
        try {
          const text = await transcribeWithElevenLabs(blob);
          if (text.trim()) onTranscript(text.trim());
        } catch {
          // ElevenLabs failed — silently fall back to idle
        } finally {
          setState("idle");
        }
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setState("recording");
    } catch {
      setState("idle");
    }
  }, [onTranscript]);

  // Start Web Speech API recognition (fallback)
  const startSpeechRecognition = useCallback(() => {
    const SpeechRecognitionCtor =
      (window as unknown as Record<string, unknown>).SpeechRecognition ||
      (window as unknown as Record<string, unknown>).webkitSpeechRecognition;
    if (!SpeechRecognitionCtor) return;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const recognition = new (SpeechRecognitionCtor as any)();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onresult = (event: any) => {
      const transcript = event.results?.[0]?.[0]?.transcript;
      if (transcript?.trim()) onTranscript(transcript.trim());
      setState("idle");
    };

    recognition.onerror = () => setState("idle");
    recognition.onend = () => setState("idle");

    recognitionRef.current = recognition;
    recognition.start();
    setState("recording");
  }, [onTranscript]);

  const stopSpeechRecognition = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  // Toggle recording
  const handleClick = useCallback(() => {
    if (state === "recording") {
      if (hasElevenLabsKey) {
        stopMediaRecorder();
      } else {
        stopSpeechRecognition();
      }
      return;
    }

    if (hasElevenLabsKey) {
      startMediaRecording();
    } else if (hasSpeechRecognition()) {
      startSpeechRecognition();
    }
  }, [
    state,
    hasElevenLabsKey,
    startMediaRecording,
    startSpeechRecognition,
    stopMediaRecorder,
    stopSpeechRecognition,
  ]);

  // Hide button if no speech method is supported
  if (!supported) return null;

  return (
    <Button
      type="button"
      variant={state === "recording" ? "destructive" : "outline"}
      size="icon"
      onClick={handleClick}
      disabled={disabled || state === "transcribing"}
      aria-label={
        state === "recording"
          ? "Stop recording"
          : state === "transcribing"
          ? "Transcribing..."
          : "Record question with voice"
      }
      className="relative shrink-0"
    >
      {state === "transcribing" ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : state === "recording" ? (
        <>
          <MicOff className="h-4 w-4" />
          <span className="absolute -top-1 -right-1 h-3 w-3 rounded-full bg-red-500 animate-pulse" />
        </>
      ) : (
        <Mic className="h-4 w-4" />
      )}
    </Button>
  );
}
