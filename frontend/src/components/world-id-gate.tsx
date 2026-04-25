"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface WorldIdGateProps {
  onSuccess: (proof: object) => void;
  onSkip?: () => void;
  demoMode?: boolean;
}

/**
 * World ID verification gate component.
 *
 * Uses @worldcoin/idkit IDKitRequestWidget when World App credentials are
 * configured. Falls back to a simulated verification for local development
 * when NEXT_PUBLIC_WORLD_APP_ID is not set.
 *
 * In demo mode, shows a bypass notice with a "Continue" button.
 */
export default function WorldIdGate({
  onSuccess,
  onSkip,
  demoMode = false,
}: WorldIdGateProps) {
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState("");
  const [widgetOpen, setWidgetOpen] = useState(false);

  const appId = process.env.NEXT_PUBLIC_WORLD_APP_ID || "";
  const action = process.env.NEXT_PUBLIC_WORLD_ACTION || "verify-human";
  const hasCredentials = appId.startsWith("app_");

  // Demo mode — skip verification entirely
  if (demoMode) {
    return (
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-xl">Identity Verification</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-center">
          <div className="rounded-lg bg-yellow-50 border border-yellow-200 p-4">
            <p className="text-sm font-medium text-yellow-800">
              🎭 Demo Mode — verification skipped
            </p>
            <p className="text-xs text-yellow-600 mt-1">
              In production, participants verify with World ID to prove they are
              human.
            </p>
          </div>
          <Button
            onClick={() => onSkip?.()}
            className="w-full"
            size="lg"
          >
            Continue without verification
          </Button>
        </CardContent>
      </Card>
    );
  }

  // Development mode — no World credentials configured
  if (!hasCredentials) {
    return (
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="text-primary"
            >
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
              <path d="m9 12 2 2 4-4" />
            </svg>
          </div>
          <CardTitle className="text-xl">Verify You&apos;re Human</CardTitle>
          <p className="text-sm text-muted-foreground mt-1">
            Powered by World ID — privacy-preserving proof of personhood
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-lg bg-blue-50 border border-blue-200 p-3">
            <p className="text-xs text-blue-700">
              <span className="font-medium">Dev mode:</span> World ID
              credentials not configured. Click below to simulate verification.
            </p>
          </div>
          {error && (
            <p className="text-sm text-red-500 text-center">{error}</p>
          )}
          <Button
            onClick={() => {
              setVerifying(true);
              setError("");
              // Simulate a short delay then return a mock proof
              setTimeout(() => {
                onSuccess({
                  merkle_root: "0x_dev_merkle_root",
                  nullifier_hash:
                    "0x_dev_nullifier_" + Math.random().toString(36).slice(2),
                  proof: "0x_dev_proof",
                  verification_level: "device",
                });
                setVerifying(false);
              }, 800);
            }}
            disabled={verifying}
            className="w-full"
            size="lg"
          >
            {verifying ? "Verifying..." : "Verify with World ID"}
          </Button>
        </CardContent>
      </Card>
    );
  }

  // Production mode — real World ID credentials available
  // Dynamically import IDKit to avoid SSR issues with WASM
  return (
    <WorldIdWidgetCard
      appId={appId as `app_${string}`}
      action={action}
      onSuccess={onSuccess}
      widgetOpen={widgetOpen}
      setWidgetOpen={setWidgetOpen}
      error={error}
      setError={setError}
    />
  );
}

/**
 * Inner component that renders the actual IDKit widget.
 * Separated so we can lazy-load the IDKit dependency.
 */
function WorldIdWidgetCard({
  appId,
  action,
  onSuccess,
  widgetOpen,
  setWidgetOpen,
  error,
  setError,
}: {
  appId: `app_${string}`;
  action: string;
  onSuccess: (proof: object) => void;
  widgetOpen: boolean;
  setWidgetOpen: (open: boolean) => void;
  error: string;
  setError: (error: string) => void;
}) {
  // We try to import the widget; if it fails we fall back to a message
  let IDKitRequestWidget: React.ComponentType<Record<string, unknown>> | null =
    null;
  let deviceLegacy: ((opts?: { signal?: string }) => unknown) | null = null;

  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const idkit = require("@worldcoin/idkit");
    IDKitRequestWidget = idkit.IDKitRequestWidget;
    deviceLegacy = idkit.deviceLegacy;
  } catch {
    // IDKit not available — show fallback
  }

  if (!IDKitRequestWidget || !deviceLegacy) {
    return (
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-xl">Verify You&apos;re Human</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-center">
          <p className="text-sm text-muted-foreground">
            World ID verification is not available in this environment.
          </p>
          <Button
            onClick={() =>
              onSuccess({
                merkle_root: "0x_fallback",
                nullifier_hash:
                  "0x_fallback_" + Math.random().toString(36).slice(2),
                proof: "0x_fallback",
                verification_level: "device",
              })
            }
            className="w-full"
            size="lg"
          >
            Continue anyway
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="text-center">
        <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-primary"
          >
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
            <path d="m9 12 2 2 4-4" />
          </svg>
        </div>
        <CardTitle className="text-xl">Verify You&apos;re Human</CardTitle>
        <p className="text-sm text-muted-foreground mt-1">
          Powered by World ID — privacy-preserving proof of personhood
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <p className="text-sm text-red-500 text-center">{error}</p>
        )}
        <IDKitRequestWidget
          app_id={appId}
          action={action}
          rp_context={{
            rp_id: appId,
            nonce: crypto.randomUUID(),
            created_at: Math.floor(Date.now() / 1000),
            expires_at: Math.floor(Date.now() / 1000) + 3600,
            signature: "placeholder_signature",
          }}
          allow_legacy_proofs={true}
          preset={deviceLegacy()}
          open={widgetOpen}
          onOpenChange={setWidgetOpen}
          onSuccess={(result: Record<string, unknown>) => {
            // Extract proof data from the IDKit result and pass upstream
            const responses = (result.responses as Array<Record<string, unknown>>) || [];
            const firstResponse = responses[0] || {};
            onSuccess({
              merkle_root: firstResponse.merkle_root || "",
              nullifier_hash:
                firstResponse.nullifier || firstResponse.nullifier_hash || "",
              proof: firstResponse.proof || "",
              verification_level: "device",
            });
          }}
          onError={(errorCode: string) => {
            setError(`Verification failed: ${errorCode}. Please try again.`);
          }}
        />
        <Button
          onClick={() => setWidgetOpen(true)}
          className="w-full"
          size="lg"
        >
          Verify with World ID
        </Button>
      </CardContent>
    </Card>
  );
}
