"use client";

export function LiveIndicator() {
  return (
    <div className="flex items-center gap-1.5">
      <style>{`
        @keyframes livePulse {
          0%, 100% {
            transform: scale(1);
            opacity: 1;
          }
          50% {
            transform: scale(1.5);
            opacity: 0.5;
          }
        }
      `}</style>
      <span
        className="inline-block h-2 w-2 rounded-full bg-green-500"
        style={{ animation: "livePulse 2s ease-in-out infinite" }}
      />
      <span className="text-xs font-semibold text-green-500 tracking-wide">
        LIVE
      </span>
    </div>
  );
}
