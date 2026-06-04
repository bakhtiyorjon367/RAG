import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios"
import { getAccessToken, setAccessToken } from "./auth-token"
import { isAbortError } from "./errors"
import { supabase } from "./supabase"

/** Same-origin on EC2 nginx when VITE_API_URL is unset or empty at build time. */
function apiBasePath(): string {
  const raw = import.meta.env.VITE_API_URL
  if (raw === undefined || raw === "") {
    return "/api/v1"
  }
  return `${String(raw).replace(/\/$/, "")}/api/v1`
}

const API_BASE = apiBasePath()

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
})

// Attach the Supabase JWT to every request (sync cache avoids auth fetch abort races).
api.interceptors.request.use(async (config) => {
  let token = getAccessToken()
  if (!token) {
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession()
      token = session?.access_token ?? null
      setAccessToken(token)
    } catch (err) {
      if (!isAbortError(err)) throw err
      token = getAccessToken()
    }
  }
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 responses: try to refresh the session and retry once
let isRefreshing = false
let refreshPromise: Promise<string | null> | null = null

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    // Only handle 401 errors, skip if already retried
    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error)
    }

    originalRequest._retry = true

    // Deduplicate concurrent refresh attempts
    if (!isRefreshing) {
      isRefreshing = true
      refreshPromise = supabase.auth
        .refreshSession()
        .then(({ data: { session } }) => {
          isRefreshing = false
          refreshPromise = null
          const token = session?.access_token ?? null
          setAccessToken(token)
          return token
        })
        .catch(() => {
          isRefreshing = false
          refreshPromise = null
          return null
        })
    }

    const newToken = await refreshPromise

    if (newToken) {
      // Retry with the new token
      originalRequest.headers.Authorization = `Bearer ${newToken}`
      return api(originalRequest)
    }

    // Refresh failed — sign out and redirect to login
    await supabase.auth.signOut()
    window.location.href = "/login"
    return Promise.reject(error)
  }
)

// ─── Documents ───────────────────────────────────────────────

export async function uploadDocument(file: File) {
  const formData = new FormData()
  formData.append("file", file)
  return api.post("/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  })
}

export async function listDocuments() {
  return api.get("/documents")
}

export async function getDocument(id: string) {
  return api.get(`/documents/${id}`)
}

export async function deleteDocument(id: string) {
  return api.delete(`/documents/${id}`)
}

export async function listChunks(
  documentId: string,
  page = 1,
  perPage = 50
) {
  return api.get(`/documents/${documentId}/chunks`, {
    params: { page, per_page: perPage },
  })
}

// ─── Search ──────────────────────────────────────────────────

export interface SearchFilters {
  document_ids?: string[]
  date_from?: string
  date_to?: string
  mime_types?: string[]
}

export interface SearchParams {
  query: string
  top_k?: number
  filters?: SearchFilters
}

export async function searchDocuments(params: SearchParams) {
  return api.post("/search", params)
}

export async function textToSQL(query: string) {
  return api.post("/search/sql", { query })
}

// ─── Chat (RAG + LLM) ────────────────────────────────────────

export interface ChatParams {
  query: string
  top_k?: number
  filters?: SearchFilters
}

export type ChatSSEEvent =
  | { type: "sources"; results: SearchResult[] }
  | { type: "token"; content: string }
  | { type: "error"; message: string }
  | { type: "done" }

interface SearchResult {
  chunk_id: string
  document_id: string
  document_name: string
  content: string
  score: number
  metadata: Record<string, unknown>
}

/**
 * Stream a RAG chat response via SSE.
 * Calls the callback for each event received.
 */
export async function chatStream(
  params: ChatParams,
  onEvent: (event: ChatSSEEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  // Get auth token from cache (same source as axios interceptor).
  const token = getAccessToken()
  if (!token) {
    const {
      data: { session },
    } = await supabase.auth.getSession()
    if (session?.access_token) {
      setAccessToken(session.access_token)
    }
  }

  const authToken = getAccessToken()

  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
    },
    body: JSON.stringify(params),
    signal,
  })

  if (!response.ok) {
    throw new Error(`Chat request failed: ${response.status}`)
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error("No response body")

  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // Parse SSE events from buffer
    const lines = buffer.split("\n")
    buffer = lines.pop() || "" // Keep incomplete line in buffer

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const event = JSON.parse(line.slice(6)) as ChatSSEEvent
          onEvent(event)
        } catch {
          // Skip malformed lines
        }
      }
    }
  }
}

export default api
