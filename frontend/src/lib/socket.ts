import { io, Socket } from "socket.io-client";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

let socket: Socket | null = null;

export function getSocket(): Socket {
  if (!socket) {
    socket = io(BACKEND_URL, {
      transports: ["websocket", "polling"],
      autoConnect: true,
    });
  }
  return socket;
}

export function joinRoom(code: string, role: "student" | "professor") {
  const s = getSocket();
  s.emit("join_room", { code, role });
}

export function leaveRoom(code: string) {
  const s = getSocket();
  s.emit("leave_room", { code });
}

export function triggerCheckin(code: string, slide: number) {
  const s = getSocket();
  s.emit("trigger_checkin", { code, slide });
}
