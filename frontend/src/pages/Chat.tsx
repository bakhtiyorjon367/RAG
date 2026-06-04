import { useCallback, useEffect, useRef, useState } from "react"
import {
  Search,
  Filter,
  X,
  Loader2,
  SearchCheck,
  Bot,
  Sparkles,
  AlertTriangle,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import {
  listDocuments,
  chatStream,
  type SearchFilters,
  type ChatSSEEvent,
} from "@/lib/api"

interface SearchResult {
  chunk_id: string
  document_id: string
  document_name: string
  content: string
  score: number
  metadata: Record<string, unknown>
}

interface Document {
  id: string
  filename: string
  mime_type: string
}

export default function Chat() {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<SearchResult[]>([])
  const [answer, setAnswer] = useState("")
  const [searching, setSearching] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [errorCode, setErrorCode] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const answerRef = useRef<HTMLDivElement>(null)

  // Filters
  const [showFilters, setShowFilters] = useState(false)
  const [documents, setDocuments] = useState<Document[]>([])
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([])
  const [selectedMimeTypes, setSelectedMimeTypes] = useState<string[]>([])

  // Load documents for filter dropdown
  useEffect(() => {
    listDocuments()
      .then(({ data }) => setDocuments(data.documents))
      .catch(console.error)
  }, [])

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return

    // Cancel any in-flight request
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setSearching(true)
    setGenerating(false)
    setHasSearched(true)
    setResults([])
    setAnswer("")
    setError(null)
    setErrorCode(null)
    try {
      const filters: SearchFilters = {}
      if (selectedDocIds.length > 0) filters.document_ids = selectedDocIds
      if (selectedMimeTypes.length > 0) filters.mime_types = selectedMimeTypes

      await chatStream(
        {
          query: query.trim(),
          top_k: 5,
          filters: Object.keys(filters).length > 0 ? filters : undefined,
        },
        (event: ChatSSEEvent) => {
          switch (event.type) {
            case "sources":
              setResults(event.results)
              setSearching(false)
              setGenerating(true)
              break
            case "token":
              setAnswer((prev) => prev + event.content)
              break
            case "error":
              setError(event.message)
              setErrorCode(event.code ?? null)
              setGenerating(false)
              break
            case "done":
              setGenerating(false)
              break
          }
        },
        controller.signal
      )
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        console.error("Chat failed:", err)
        setError("Failed to get a response. Please try again.")
      }
    } finally {
      setSearching(false)
      setGenerating(false)
    }
  }, [query, selectedDocIds, selectedMimeTypes])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSearch()
  }

  const toggleDocFilter = (docId: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(docId)
        ? prev.filter((id) => id !== docId)
        : [...prev, docId]
    )
  }

  const toggleMimeFilter = (mime: string) => {
    setSelectedMimeTypes((prev) =>
      prev.includes(mime)
        ? prev.filter((m) => m !== mime)
        : [...prev, mime]
    )
  }

  const clearFilters = () => {
    setSelectedDocIds([])
    setSelectedMimeTypes([])
  }

  const hasActiveFilters =
    selectedDocIds.length > 0 || selectedMimeTypes.length > 0

  const isGeminiQuotaError =
    errorCode === "gemini_quota_exceeded" || errorCode === "gemini_rate_limited"

  return (
    <div className="w-full space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Ask</h1>
        <p className="text-muted-foreground">
          Ask natural-language questions — AI will answer using your documents.
        </p>
      </div>

      {/* Search Input */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-10"
            placeholder="Ask a question about your documents..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
          />
        </div>
        <Button onClick={handleSearch} disabled={searching || generating || !query.trim()}>
          {searching || generating ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <>
              <Sparkles className="h-4 w-4 mr-1" />
              Ask
            </>
          )}
        </Button>
        <Button
          variant={showFilters ? "secondary" : "outline"}
          size="icon"
          onClick={() => setShowFilters(!showFilters)}
          className="relative"
        >
          <Filter className="h-4 w-4" />
          {hasActiveFilters && (
            <span className="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-primary" />
          )}
        </Button>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium">Filters</h3>
              {hasActiveFilters && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearFilters}
                  className="gap-1 h-7 text-xs"
                >
                  <X className="h-3 w-3" /> Clear all
                </Button>
              )}
            </div>

            {/* Format Filters */}
            <div className="mb-4">
              <p className="text-xs font-medium text-muted-foreground mb-2">
                Format
              </p>
              <div className="flex flex-wrap gap-2">
                {[
                  { mime: "application/pdf", label: "PDF" },
                  {
                    mime: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    label: "DOCX",
                  },
                  { mime: "text/html", label: "HTML" },
                  { mime: "text/markdown", label: "Markdown" },
                ].map(({ mime, label }) => (
                  <Badge
                    key={mime}
                    variant={
                      selectedMimeTypes.includes(mime) ? "default" : "outline"
                    }
                    className="cursor-pointer"
                    onClick={() => toggleMimeFilter(mime)}
                  >
                    {label}
                  </Badge>
                ))}
              </div>
            </div>

            <Separator className="my-4" />

            {/* Document Filters */}
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-2">
                Documents
              </p>
              <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto">
                {documents.map((doc) => (
                  <Badge
                    key={doc.id}
                    variant={
                      selectedDocIds.includes(doc.id) ? "default" : "outline"
                    }
                    className="cursor-pointer"
                    onClick={() => toggleDocFilter(doc.id)}
                  >
                    {doc.filename}
                  </Badge>
                ))}
                {documents.length === 0 && (
                  <p className="text-xs text-muted-foreground">
                    No documents uploaded yet.
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Loading search */}
      {searching && (
        <div className="flex items-center justify-center py-12">
          <div className="flex items-center gap-3 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span>Searching documents...</span>
          </div>
        </div>
      )}

      {/* Error — shown before answer so quota failures are visible */}
      {error && isGeminiQuotaError && (
        <Alert className="border-amber-500/50 bg-amber-500/5">
          <AlertTriangle className="text-amber-600 dark:text-amber-500" />
          <AlertTitle>
            {errorCode === "gemini_quota_exceeded"
              ? "Gemini free tier is over"
              : "Gemini rate limit reached"}
          </AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {error && !isGeminiQuotaError && (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="pt-6">
            <p className="text-sm text-destructive">{error}</p>
          </CardContent>
        </Card>
      )}

      {/* AI Answer */}
      {(answer || generating) && (
        <div className="flex gap-3">
          <Bot className="h-6 w-6 text-primary shrink-0 mt-0.5" />
          <div className="min-w-0 flex-1">
            {generating && !answer && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm">Thinking...</span>
              </div>
            )}
            <div
              ref={answerRef}
              className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap"
            >
              {answer}
            </div>
            {generating && answer && (
              <Loader2 className="h-3.5 w-3.5 animate-spin text-primary mt-2" />
            )}
          </div>
        </div>
      )}

      {/* No results */}
      {!searching && hasSearched && results.length === 0 && !answer && !generating && (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <SearchCheck className="h-12 w-12 text-muted-foreground/50" />
          <p className="mt-4 text-lg font-medium">No results found</p>
          <p className="text-sm text-muted-foreground">
            Try rephrasing your question or uploading more documents.
          </p>
        </div>
      )}

      {/* Empty state — no search yet */}
      {!hasSearched && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <SearchCheck className="h-16 w-16 text-muted-foreground/30" />
          <p className="mt-6 text-lg font-medium">Ready to search</p>
          <p className="mt-1 text-sm text-muted-foreground max-w-md">
            Type a question above to search across all your uploaded documents.
            AI will generate an answer based on the most relevant passages.
          </p>
        </div>
      )}
    </div>
  )
}
