/**
 * WebSocket-based interview protocol client (v4 / AURA).
 * Persistent connection replaces HTTP request/response for the interview flow.
 *
 * Protocol (JSON messages over WebSocket):
 * Client → Server: { _id, type, ...data }
 * Server → Client: { _id, type, ...data }   (_id echoed to resolve requests)
 * Server → Client (pushes): { type: "status", phase: "evaluating" | "question_ready" }
 *
 * Requests resolve when a message matches BOTH the pending _id AND the expected
 * response type — so "status" pushes never satisfy a pending request.
 */

import { getCandidateToken } from '../utils/candidateToken';

type Listener = (data: any) => void;

interface PendingEntry {
  resolve: (data: any) => void;
  reject: (err: Error) => void;
  timeout: ReturnType<typeof setTimeout>;
}

export class InterviewWebSocket {
  private ws: WebSocket | null = null;
  private baseUrl: string;
  private pendingResolvers = new Map<string, PendingEntry>();
  private pendingTypes = new Map<string, string>();
  private listeners = new Map<string, Set<Listener>>();
  private messageId = 0;

  constructor(baseUrl: string = '') {
    this.baseUrl = baseUrl.replace(/^http/, 'ws');
  }

  async connect(sessionId: string): Promise<void> {
    if (this.ws) {
      // Replacing an existing socket: detach its handlers so its close is
      // treated as intentional and does not trigger a reconnect cycle.
      this.ws.onclose = null;
      this.ws.close();
      this.ws = null;
    }
    const token = getCandidateToken();
    const url = token
      ? `${this.baseUrl}/ws/interview/${sessionId}?token=${token}`
      : `${this.baseUrl}/ws/interview/${sessionId}`;
    const ws = new WebSocket(url);
    this.ws = ws;

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('WebSocket connection timeout'));
      }, 10000);

      ws.onopen = () => {
        clearTimeout(timeout);
        resolve();
      };

      ws.onerror = () => {
        clearTimeout(timeout);
        reject(new Error('WebSocket connection failed'));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data._id && this.pendingResolvers.has(data._id)) {
            const expected = this.pendingTypes.get(data._id);
            if (expected && expected.split('|').includes(data.type)) {
              this.pendingTypes.delete(data._id);
              const entry = this.pendingResolvers.get(data._id)!;
              clearTimeout(entry.timeout);
              this.pendingResolvers.delete(data._id);
              if (data.type === 'error') {
                entry.reject(new Error(data.detail || 'Request failed'));
              } else {
                entry.resolve(data);
              }
            }
          }

          this.dispatch(data.type, data);
        } catch {
          // Ignore malformed messages
        }
      };

      ws.onclose = (event) => {
        const manual = ws !== this.ws;
        for (const [_, entry] of this.pendingResolvers) {
          clearTimeout(entry.timeout);
          entry.reject(new Error('WebSocket closed'));
        }
        this.pendingResolvers.clear();
        this.pendingTypes.clear();
        if (manual) {
          if (this.ws === ws) this.ws = null;
        } else {
          this.dispatch('close', { type: 'close', code: event.code, reason: event.reason });
        }
      };
    });
  }

  on(type: string, listener: Listener): () => void {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set());
    }
    this.listeners.get(type)!.add(listener);
    return () => this.off(type, listener);
  }

  off(type: string, listener: Listener): void {
    this.listeners.get(type)?.delete(listener);
  }

  private dispatch(type: string, data: any): void {
    this.listeners.get(type)?.forEach((listener) => {
      try {
        listener(data);
      } catch {
        // Listener errors must not break the socket loop
      }
    });
  }

  private async sendAndWait(type: string, payload: Record<string, unknown>, expectedTypes: string[], timeoutMs = 120000): Promise<any> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }

    const id = String(++this.messageId);
    const message = { _id: id, type, ...payload };
    this.ws.send(JSON.stringify(message));

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pendingResolvers.delete(id);
        this.pendingTypes.delete(id);
        reject(new Error(`Request ${type} timed out after ${timeoutMs}ms`));
      }, timeoutMs);

      this.pendingResolvers.set(id, { resolve, reject, timeout });
      this.pendingTypes.set(id, expectedTypes.join('|'));
    });
  }

  async startSession(params: {
    session_id: string;
    department_id?: number;
    job_role?: string;
  }): Promise<any> {
    return this.sendAndWait('start_interview', params, ['question']);
  }

  async getNextQuestion(params: {
    session_id: string;
  }): Promise<any> {
    return this.sendAndWait('request_question', params, ['question']);
  }

  async submitAnswer(params: {
    session_id: string;
    question_number?: number;
    question?: string;
    candidate_answer: string;
  }): Promise<any> {
    return this.sendAndWait('submit_answer', params as Record<string, unknown>, ['evaluation', 'report']);
  }

  async getStatus(session_id: string): Promise<any> {
    return this.sendAndWait('get_status', { session_id }, ['status_snapshot']);
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
    this.pendingTypes.clear();
    this.listeners.clear();
  }

  get connected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}

export const interviewWebSocket = new InterviewWebSocket(
  (typeof window !== 'undefined' && (window as any).__INTERVIEW_WS_URL) || 'ws://localhost:8000'
);
