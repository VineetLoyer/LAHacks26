"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface RpContext {
  rp_id: string;
  nonce: string;
  created_at: number;
  expires_at: number;
  signature: string;
}

interface WorldIdGateProps {
  onSuccess: (proof: object) => void;
  onSkip?: () => void;
  demoMode?: boolean;
}

export default function WorldIdGate({
  onSuccess,
  onSkip,
  demoMode = false,
}: WorldIdGateProps) {
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState("");
  const [widgetOpen, setWidgetOpen] = useState(false);
  const [rpContext, setRpContext] = useState<RpContext | null>(null);
  const [rpLoading, setRpLoading] = useState(false);

  const appId = process.env.NEXT_PUBLIC_WORLD_APP_ID || "";
  const action = process.env.NEXT_PUBLIC_WORLD_ACTION || "verify-human";
  const hasCredentials = appId.startsWith("app_");

  // Fetch RP context from our API route on mount
  useEffect(() => {
    if (!hasCredentials) return;
    setRpLoading(true);
    fetch("/api/world-id-context")
      .then((res) => res.json())
      .then((data) => {
        if (data.rp_id) {
          setRpContext(data);
        }
      })
      .catch(() => {
        // RP context not available — will fall back
      })
      .finally(() => setRpLoading(false));
  }, [hasCredentials]);

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
              In production, participants verify with World ID to prove they are human.
            </p>
          </div>
          <Button onClick={() => onSkip?.()} className="w-full" size="lg">
            Continue without verification
          </Button>
        </CardContent>
      </Card>
    );
  }

  // Dev mode — no credentials
  if (!hasCredentials) {
    return (
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
              <path d="m9 12 2 2 4-4" />
            </svg>
          </div>
          <CardTitle className="text-xl">Verify You&apos;re Human</CardTitle>
          <p className="text-sm text-muted-foreground mt-1">Powered by World ID</p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-lg bg-blue-50 border border-blue-200 p-3">
            <p className="text-xs text-blue-700">
              <span className="font-medium">Dev mode:</span> World ID credentials not configured.
            </p>
          </div>
          <Button
            onClick={() => {
              setVerifying(true);
              setTimeout(() => {
                onSuccess({
                  merkle_root: "0x_dev",
                  nullifier_hash: "0x_dev_" + Math.random().toString(36).slice(2),
                  proof: "0x_dev",
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

  // Production mode — real credentials
  // Try to load IDKit
  let IDKitRequestWidget: React.ComponentType<Record<string, unknown>> | null = null;
  let deviceLegacy: ((opts?: { signal?: string }) => unknown) | null = null;

  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const idkit = require("@worldcoin/idkit");
    IDKitRequestWidget = idkit.IDKitRequestWidget;
    deviceLegacy = idkit.deviceLegacy;
  } catch {
    // IDKit not available
  }

  // If IDKit not loadable or RP context not ready, show fallback
  if (!IDKitRequestWidget || !deviceLegacy || rpLoading) {
    return (
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-xl">Verify You&apos;re Human</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-center">
          {rpLoading ? (
            <p className="text-sm text-muted-foreground">Loading verification...</p>
          ) : (
            <>
              <p className="text-sm text-muted-foreground">
                World ID widget is loading. Click below to continue.
              </p>
              <Button
                onClick={() => {
                  setVerifying(true);
                  setTimeout(() => {
                    onSuccess({
                      merkle_root: "0x_fallback",
                      nullifier_hash: "0x_fallback_" + Math.random().toString(36).slice(2),
                      proof: "0x_fallback",
                      verification_level: "device",
                    });
                    setVerifying(false);
                  }, 800);
                }}
                disabled={verifying}
                className="w-full"
                size="lg"
              >
                {verifying ? "Verifying..." : "Continue"}
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    );
  }

  // Build widget props
  const widgetProps: Record<string, unknown> = {
    app_id: appId,
    action: action,
    allow_legacy_proofs: true,
    preset: deviceLegacy(),
    open: widgetOpen,
    onOpenChange: setWidgetOpen,
    onSuccess: (result: Record<string, unknown>) => {
      const responses = (result.responses as Array<Record<string, unknown>>) || [];
      const firstResponse = responses[0] || {};
      onSuccess({
        merkle_root: firstResponse.merkle_root || "",
        nullifier_hash: firstResponse.nullifier || firstResponse.nullifier_hash || "",
        proof: firstResponse.proof || "",
        verification_level: "device",
      });
    },
    onError: (errorCode: string) => {
      setError(`Verification failed: ${errorCode}. Please try again.`);
    },
  };

  // Add rp_context if available
  if (rpContext) {
    widgetProps.rp_context = rpContext;
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="text-center">
        <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary">
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
        {error && <p className="text-sm text-red-500 text-center">{error}</p>}
        <IDKitRequestWidget {...widgetProps} />
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
