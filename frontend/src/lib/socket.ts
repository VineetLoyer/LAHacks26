import { io, Socket } from "socket.io-client";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

let socket: Socket | null = null;
let pendingRoom: { code: string; role: string } | null = null;

export function getSocket(): Socket {
  if (!socket) {
    socket = io(BACKEND_URL, {
      transports: ["websocket", "polling"],
      autoConnect: true,
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 1000,
    });

    // Auto re-join room on reconnect
    socket.on("connect", () => {
      if (pendingRoom) {
        socket!.emit("join_room", pendingRoom);
      }
    });
  }
  return socket;
}

/** Join a room. Stores room info so we auto-rejoin on reconnect. */
export function joinRoom(code: string, role: "student" | "professor") {
  pendingRoom = { code, role };
  const s = getSocket();
  if (s.connected) {
    s.emit("join_room", { code, role });
  }
  // If not connected, the "connect" handler above will emit join_room
}

export function leaveRoom(code: string) {
  pendingRoom = null;
  const s = getSocket();
  s.emit("leave_room", { code });
}

export function triggerCheckin(code: string, slide: number) {
  const s = getSocket();
  s.emit("trigger_checkin", { code, slide });
}
