import { useCallback, useEffect, useState } from "react"
import { Search as SearchIcon, Filter, X, Loader2, SearchCheck } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { searchDocuments, listDocuments, type SearchFilters } from "@/lib/api"

interface SearchResultItem {
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

export default function Search() {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<SearchResultItem[]>([])
  const [searching, setSearching] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [showFilters, setShowFilters] = useState(false)
  const [documents, setDocuments] = useState<Document[]>([])
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([])
  const [selectedMimeTypes, setSelectedMimeTypes] = useState<string[]>([])

  useEffect(() => {
    listDocuments()
      .then(({ data }) => setDocuments(data.documents))
      .catch(console.error)
  }, [])

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return

    setSearching(true)
    setHasSearched(true)
    setResults([])
    setError(null)
    try {
      const filters: SearchFilters = {}
      if (selectedDocIds.length > 0) filters.document_ids = selectedDocIds
      if (selectedMimeTypes.length > 0) filters.mime_types = selectedMimeTypes

      const { data } = await searchDocuments({
        query: query.trim(),
        top_k: 10,
        filters: Object.keys(filters).length > 0 ? filters : undefined,
      })
      setResults(data.results ?? [])
    } catch (err) {
      console.error("Search failed:", err)
      setError("Search failed. Please try again.")
    } finally {
      setSearching(false)
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

  return (
    <div className="w-full space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Search</h1>
        <p className="text-muted-foreground">
          Chunk-only search — no AI answer. See ranked passages from your documents.
        </p>
      </div>

      <div className="flex gap-2">
        <div className="relative flex-1">
          <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-10"
            placeholder="Search your documents..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
          />
        </div>
        <Button
          onClick={handleSearch}
          disabled={searching || !query.trim()}
        >
          {searching ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            "Search"
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

      {searching && (
        <div className="flex items-center justify-center py-12">
          <div className="flex items-center gap-3 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span>Searching...</span>
          </div>
        </div>
      )}

      {error && (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="pt-6">
            <p className="text-sm text-destructive">{error}</p>
          </CardContent>
        </Card>
      )}

      {!searching && hasSearched && results.length === 0 && !error && (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <SearchCheck className="h-12 w-12 text-muted-foreground/50" />
          <p className="mt-4 text-lg font-medium">No results found</p>
          <p className="text-sm text-muted-foreground">
            Try different keywords or filters.
          </p>
        </div>
      )}

      {!searching && results.length > 0 && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            {results.length} result{results.length !== 1 ? "s" : ""}
          </p>
          <div className="space-y-3">
            {results.map((r) => (
              <Card key={r.chunk_id}>
                <CardContent className="pt-4">
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="text-sm font-medium text-primary">
                      {r.document_name}
                    </span>
                    <Badge variant="secondary">
                      score {(r.score ?? 0).toFixed(3)}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                    {r.content}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {!hasSearched && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <SearchCheck className="h-16 w-16 text-muted-foreground/30" />
          <p className="mt-6 text-lg font-medium">Chunk-only search</p>
          <p className="mt-1 text-sm text-muted-foreground max-w-md">
            Enter a query to get ranked document chunks. No AI answer — just
            the matching passages.
          </p>
        </div>
      )}
    </div>
  )
}
