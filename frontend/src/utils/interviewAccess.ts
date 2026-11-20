/**
 * Per-session interview access tokens (for guests without an account).
 *
 * The invitation / public start hands out a token bound to one interview session; the
 * interview WebSocket needs it. Kept in sessionStorage so a page refresh keeps working
 * but the credential does not outlive the tab.
 */
const key = (sessionId: string) => `interview_access_${sessionId}`;

export function setInterviewAccess(sessionId: string, token: string | null | undefined): void {
  if (!token) return;
  try {
    sessionStorage.setItem(key(sessionId), token);
  } catch {
    /* storage unavailable (private mode): the logged-in candidate token still works */
  }
}

export function getInterviewAccess(sessionId: string): string | null {
  try {
    return sessionStorage.getItem(key(sessionId));
  } catch {
    return null;
  }
}
