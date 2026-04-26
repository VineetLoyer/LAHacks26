const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

// --- Sessions ---
export function createSession(data: {
  title: string;
  anonymous_mode: boolean;
  confusion_threshold: number;
  demo_mode?: boolean;
}) {
  return request<{ id: string; code: string; title: string }>(
    "/api/sessions/create",
    { method: "POST", body: JSON.stringify(data) }
  );
}

export function getSessionStats(sessionId: string) {
  return request<{
    confusion_index: number;
    total_questions: number;
    participant_count: number;
    demo_mode: boolean;
    confusion_threshold: number;
    cluster_count: number;
  }>(`/api/sessions/${sessionId}/stats`);
}

export function joinSession(code: string) {
  return request<{
    id: string;
    title: string;
    anonymous_mode: boolean;
    current_slide: number;
    demo_mode: boolean;
  }>(`/api/sessions/join/${code.toUpperCase()}`);
}

// --- Check-ins ---
export function submitCheckin(data: {
  session_id: string;
  confusion_rating: number;
  slide?: number;
}) {
  return request<{ confusion_index: number; total_checkins: number }>(
    "/api/checkins/submit",
    { method: "POST", body: JSON.stringify(data) }
  );
}

export function getConfusionStats(sessionId: string) {
  return request<{
    timeline: Array<{
      slide: number;
      confusion_pct: number;
      avg_rating: number;
      responses: number;
    }>;
  }>(`/api/checkins/stats/${sessionId}`);
}

// --- Questions ---
export function submitQuestion(data: {
  session_id: string;
  text: string;
  slide?: number;
}) {
  return request<{ id: string; status: string }>("/api/questions/submit", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function listQuestions(sessionId: string) {
  return request<{
    questions: Array<{
      id: string;
      text: string;
      slide: number | null;
      cluster_id: string | null;
      timestamp: string;
    }>;
  }>(`/api/questions/list/${sessionId}`);
}

// --- Clusters ---
export function generateClusters(sessionId: string) {
  return request<{
    clusters: Array<{
      id: string;
      label: string;
      question_count: number;
      representative_question: string;
      summary: string;
      on_topic: boolean;
    }>;
    message?: string;
  }>(`/api/clusters/generate/${sessionId}`, { method: "POST" });
}

export function listClusters(sessionId: string) {
  return request<{
    clusters: Array<{
      id: string;
      label: string;
      question_count: number;
      representative_question: string;
      summary: string;
      upvotes: number;
      status: string;
      on_topic: boolean;
      ai_explanation: string | null;
      professor_response: string | null;
      response_type: string | null;
    }>;
  }>(`/api/clusters/list/${sessionId}`);
}

export function upvoteCluster(clusterId: string) {
  return request<{ status: string; upvotes: number }>(`/api/clusters/upvote/${clusterId}`, {
    method: "POST",
  });
}

export function downvoteCluster(clusterId: string) {
  return request<{ status: string; upvotes: number }>(`/api/clusters/downvote/${clusterId}`, {
    method: "POST",
  });
}

export function hideCluster(clusterId: string) {
  return request<{ cluster_id: string; status: string }>(
    `/api/clusters/${clusterId}/hide`,
    { method: "PATCH" }
  );
}

export function restoreCluster(clusterId: string) {
  return request<{ cluster_id: string; status: string }>(
    `/api/clusters/${clusterId}/restore`,
    { method: "PATCH" }
  );
}

export function addressCluster(data: {
  cluster_id: string;
  response_type: string;
  custom_response?: string;
}) {
  return request<{
    cluster_id: string;
    ai_explanation: string;
    response_type: string;
    status: string;
  }>("/api/clusters/address", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// --- Auth ---
export function verifyWorldId(data: {
  proof: object;
  session_code: string;
}) {
  return request<{ verified: boolean; simulated?: boolean }>(
    "/api/auth/verify-world-id",
    { method: "POST", body: JSON.stringify(data) }
  );
}


// --- Reports ---
export interface ReportData {
  id: string;
  total_participants: number;
  total_questions: number;
  clusters_addressed: number;
  clusters_total: number;
  confusion_timeline: Array<{
    slide: number;
    confusion_pct: number;
    avg_rating: number;
    responses: number;
  }>;
  confusion_spikes: Array<{
    slide: number;
    confusion_pct: number;
    description: string;
  }>;
  flagged_for_next_lecture: string[];
  summary: string;
  generated_at: string;
  feedback_summary?: {
    average_rating: number;
    total_count: number;
  };
}

export function generateReport(sessionId: string) {
  return request<ReportData>(`/api/reports/generate/${sessionId}`, {
    method: "POST",
  });
}

export function getReport(sessionId: string) {
  return request<ReportData>(`/api/reports/${sessionId}`);
}

// --- Sessions (file upload) ---
export async function createSessionWithFile(formData: FormData) {
  const res = await fetch(
    `${API_BASE}/api/sessions/create-with-file`,
    { method: "POST", body: formData }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json() as Promise<{
    id: string;
    code: string;
    title: string;
    slides_extracted: number;
  }>;
}

export function getSlideContexts(sessionId: string) {
  return request<{
    slides: Array<{ slide_number: number; text_content: string }>;
  }>(`/api/sessions/${sessionId}/slides`);
}

// --- Email Opt-In ---
export function optInEmail(sessionId: string, email: string) {
  return request<{ status: string; email: string }>(
    `/api/sessions/${sessionId}/opt-in-email`,
    { method: "POST", body: JSON.stringify({ email }) }
  );
}

export function sendSummary(sessionId: string) {
  return request<{ emails_sent: number; summary: string; message: string }>(
    `/api/sessions/${sessionId}/send-summary`,
    { method: "POST" }
  );
}

// --- Feedback ---
export function submitFeedback(sessionId: string, data: { rating: number; comment?: string }) {
  return request<{ status: string }>(`/api/sessions/${sessionId}/feedback`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function getFeedbackSummary(sessionId: string) {
  return request<{
    average_rating: number;
    total_count: number;
    distribution: Record<string, number>;
    useful_comments: string[];
    summary_bullets: string[];
    raw_comment_count: number;
  }>(`/api/sessions/${sessionId}/feedback-summary`);
}
