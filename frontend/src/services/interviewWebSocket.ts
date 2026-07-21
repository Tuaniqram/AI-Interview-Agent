/**
 * WebSocket-based interview protocol client.
 * Replaces HTTP request/response with a persistent connection for the interview flow.
 * 
 * Protocol (JSON messages over WebSocket):
 * Client → Server: { type, ...data }
 * Server → Client: { type, ...data }
 */

export class InterviewWebSocket {
  private ws: WebSocket | null = null;
  private baseUrl: string;
  private pendingResolvers = new Map<string, {
    resolve: (data: any) => void;
    reject: (err: Error) => void;
    timeout: ReturnType<typeof setTimeout>;
  }>();
  private messageId = 0;

  constructor(baseUrl: string = '') {
    this.baseUrl = baseUrl.replace(/^http/, 'ws');
  }

  async connect(sessionId: string): Promise<void> {
    const url = `${this.baseUrl}/ws/interview/${sessionId}`;
    this.ws = new WebSocket(url);

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('WebSocket connection timeout'));
      }, 10000);

      this.ws!.onopen = () => {
        clearTimeout(timeout);
        resolve();
      };

      this.ws!.onerror = () => {
        clearTimeout(timeout);
        reject(new Error('WebSocket connection failed'));
      };

      this.ws!.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data._id && this.pendingResolvers.has(data._id)) {
            const entry = this.pendingResolvers.get(data._id)!;
            clearTimeout(entry.timeout);
            this.pendingResolvers.delete(data._id);
            entry.resolve(data);
          }
        } catch {
          // Ignore malformed messages
        }
      };

      this.ws!.onclose = () => {
        for (const [_, entry] of this.pendingResolvers) {
          clearTimeout(entry.timeout);
          entry.reject(new Error('WebSocket closed'));
        }
        this.pendingResolvers.clear();
      };
    });
  }

  private async sendAndWait(type: string, payload: Record<string, unknown>, timeoutMs = 30000): Promise<any> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }

    const id = String(++this.messageId);
    const message = { _id: id, type, ...payload };
    this.ws.send(JSON.stringify(message));

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pendingResolvers.delete(id);
        reject(new Error(`Request ${type} timed out after ${timeoutMs}ms`));
      }, timeoutMs);

      this.pendingResolvers.set(id, { resolve, reject, timeout });
    });
  }

  async startSession(params: {
    company_id: number;
    job_role: string;
    candidate_id?: string;
    candidate_name?: string;
    candidate_email?: string;
    total_questions?: number;
    initial_difficulty?: number;
    interview_type?: string;
    interview_mode?: string;
  }): Promise<any> {
    return this.sendAndWait('start_interview', params as Record<string, unknown>);
  }

  async getNextQuestion(params: {
    session_id: string;
    conversation_history?: Array<{ role: string; content: string }>;
    current_phase?: string;
    question_number?: number;
    difficulty_level?: number;
    candidate_profile?: Record<string, unknown>;
  }): Promise<any> {
    return this.sendAndWait('request_question', params as Record<string, unknown>);
  }

  async submitAnswer(params: {
    session_id: string;
    question_number: number;
    question: string;
    candidate_answer: string;
    conversation_history?: Array<{ role: string; content: string }>;
    candidate_profile?: Record<string, unknown>;
    difficulty_level?: number;
  }): Promise<any> {
    return this.sendAndWait('submit_answer', params as Record<string, unknown>);
  }

  async getStatus(session_id: string): Promise<any> {
    return this.sendAndWait('get_status', { session_id });
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    for (const [_, entry] of this.pendingResolvers) {
      clearTimeout(entry.timeout);
      entry.reject(new Error('WebSocket disconnected'));
    }
    this.pendingResolvers.clear();
  }

  get connected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}

export const interviewWebSocket = new InterviewWebSocket(
  (typeof window !== 'undefined' && (window as any).__INTERVIEW_WS_URL) || 'ws://localhost:8000'
);
