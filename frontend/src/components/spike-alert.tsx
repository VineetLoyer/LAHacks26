"use client";

import { useEffect } from "react";
import { Alert, AlertTitle, AlertAction } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { XIcon } from "lucide-react";

interface SpikeAlertProps {
  message: string;
  visible: boolean;
  onDismiss: () => void;
}

export function SpikeAlert({ message, visible, onDismiss }: SpikeAlertProps) {
  useEffect(() => {
    if (!visible) return;
    const timer = setTimeout(onDismiss, 10000);
    return () => clearTimeout(timer);
  }, [visible, onDismiss]);

  if (!visible) return null;

  return (
    <>
      <style>{`
        @keyframes slideDown {
          from {
            transform: translateY(-100%);
            opacity: 0;
          }
          to {
            transform: translateY(0);
            opacity: 1;
          }
        }
        @keyframes spikePulse {
          0%, 100% {
            box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4);
          }
          50% {
            box-shadow: 0 0 16px 4px rgba(239, 68, 68, 0.3);
          }
        }
      `}</style>
      <Alert
        variant="destructive"
        className="border-red-500 bg-red-500 text-white *:data-[slot=alert-description]:text-white/90"
        style={{
          animation: "slideDown 0.3s ease-out, spikePulse 2s ease-in-out infinite",
        }}
      >
        <AlertTitle className="text-white font-semibold">{message}</AlertTitle>
        <AlertAction>
          <Button
            variant="ghost"
            size="icon-sm"
            className="text-white hover:bg-white/20"
            onClick={onDismiss}
          >
            <XIcon className="h-4 w-4" />
          </Button>
        </AlertAction>
      </Alert>
    </>
  );
}
