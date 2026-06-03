/** In-memory JWT cache so API calls avoid concurrent supabase.auth.getSession() aborts. */
let accessToken: string | null = null

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}
