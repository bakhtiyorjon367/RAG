import { useCallback, useEffect, useState } from "react"
import {
  Upload,
  FileText,
  FileType,
  Globe,
  Hash,
  Trash2,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Clock,
  Loader2,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { deleteDocument, listDocuments, uploadDocument } from "@/lib/api"
import { isAbortError } from "@/lib/errors"
import { supabase } from "@/lib/supabase"
import { useAuth } from "@/hooks/useAuth"

interface Document {
  id: string
  filename: string
  mime_type: string
  status: "pending" | "processing" | "ready" | "error"
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

const ACCEPTED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "text/html",
  "text/markdown",
  "text/plain",
]

const ACCEPT_STRING = ".pdf,.docx,.html,.md,.markdown,.txt"

function getMimeIcon(mimeType: string) {
  if (mimeType.includes("pdf")) return <FileText className="h-4 w-4 text-red-500" />
  if (mimeType.includes("word") || mimeType.includes("docx"))
    return <FileType className="h-4 w-4 text-blue-500" />
  if (mimeType.includes("html")) return <Globe className="h-4 w-4 text-orange-500" />
  if (mimeType === "text/plain") return <FileText className="h-4 w-4 text-gray-500" />
  return <Hash className="h-4 w-4 text-green-500" />
}

function getStatusBadge(status: string) {
  switch (status) {
    case "pending":
      return (
        <Badge variant="secondary" className="gap-1">
          <Clock className="h-3 w-3" /> Pending
        </Badge>
      )
    case "processing":
      return (
        <Badge variant="secondary" className="gap-1 bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200">
          <Loader2 className="h-3 w-3 animate-spin" /> Processing
        </Badge>
      )
    case "ready":
      return (
        <Badge variant="secondary" className="gap-1 bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
          <CheckCircle2 className="h-3 w-3" /> Ready
        </Badge>
      )
    case "error":
      return (
        <Badge variant="destructive" className="gap-1">
          <AlertCircle className="h-3 w-3" /> Error
        </Badge>
      )
    default:
      return <Badge variant="outline">{status}</Badge>
  }
}

export default function Ingest() {
  const { user } = useAuth()
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState("")
  const [dragOver, setDragOver] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<Document | null>(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    if (!user) return

    let cancelled = false
    setLoading(true)

    ;(async () => {
      try {
        const { data } = await listDocuments()
        if (!cancelled) setDocuments(data.documents)
      } catch (err) {
        if (!cancelled && !isAbortError(err)) {
          console.error("Failed to fetch documents:", err)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [user?.id])

  const fetchDocuments = useCallback(async () => {
    if (!user) return
    try {
      const { data } = await listDocuments()
      setDocuments(data.documents)
    } catch (err) {
      if (!isAbortError(err)) {
        console.error("Failed to fetch documents:", err)
      }
    }
  }, [user])

  // Realtime for live status updates (optional; list still works via REST).
  useEffect(() => {
    if (!user) return

    let active = true
    const channel = supabase
      .channel(`documents:${user.id}`)
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "documents",
        },
        (payload) => {
          const rowUserId =
            (payload.new as { user_id?: string } | undefined)?.user_id ??
            (payload.old as { user_id?: string } | undefined)?.user_id
          if (rowUserId !== user.id) return

          if (payload.eventType === "UPDATE" || payload.eventType === "INSERT") {
            setDocuments((prev) => {
              const updated = payload.new as Document
              const exists = prev.find((d) => d.id === updated.id)
              if (exists) {
                return prev.map((d) => (d.id === updated.id ? updated : d))
              }
              return [updated, ...prev]
            })
          } else if (payload.eventType === "DELETE") {
            setDocuments((prev) =>
              prev.filter((d) => d.id !== (payload.old as Document).id)
            )
          }
        }
      )
      .subscribe((status, err) => {
        if (!active) return
        if (status === "CHANNEL_ERROR") {
          console.warn("Document realtime subscription failed:", err?.message)
        }
      })

    return () => {
      active = false
      void supabase.removeChannel(channel)
    }
  }, [user?.id])

  // Upload handler
  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return
    setUploadError("")
    setUploading(true)

    try {
      for (const file of Array.from(files)) {
        if (!ACCEPTED_TYPES.includes(file.type) && !file.name.endsWith(".md") && !file.name.endsWith(".txt")) {
          setUploadError(
            `Unsupported file type: ${file.name}. Supported: PDF, DOCX, HTML, Markdown, TXT.`
          )
          continue
        }
        if (file.size > 50 * 1024 * 1024) {
          setUploadError(`File too large: ${file.name}. Max size is 50 MB.`)
          continue
        }
        await uploadDocument(file)
      }
      await fetchDocuments()
    } catch (err: unknown) {
      if (err && typeof err === "object" && "response" in err) {
        const axiosErr = err as { response?: { status: number; data?: { detail?: string | { message?: string } } } }
        if (axiosErr.response?.status === 409) {
          const detail = axiosErr.response.data?.detail
          const message = typeof detail === "string" ? detail : detail?.message || "Duplicate document"
          setUploadError(message)
        } else {
          setUploadError("Upload failed. Please try again.")
        }
      } else {
        setUploadError("Upload failed. Please try again.")
      }
    } finally {
      setUploading(false)
    }
  }

  // Delete handler
  const handleDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteDocument(deleteTarget.id)
      setDocuments((prev) => prev.filter((d) => d.id !== deleteTarget.id))
      setDeleteTarget(null)
    } catch {
      console.error("Failed to delete document")
    } finally {
      setDeleting(false)
    }
  }

  // Drag and drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }

  const handleDragLeave = () => {
    setDragOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    handleUpload(e.dataTransfer.files)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Documents</h1>
        <p className="text-muted-foreground">
          Upload and manage your documents for search.
        </p>
      </div>

      {/* Upload Area */}
      <Card>
        <CardHeader>
          <CardTitle>Upload Documents</CardTitle>
          <CardDescription>
            Drag and drop files or click to browse. Supported formats: PDF, DOCX,
            HTML, Markdown, TXT. Max size: 50 MB.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            className={`
              flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-12
              transition-colors cursor-pointer
              ${dragOver ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:border-primary/50"}
            `}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => document.getElementById("file-input")?.click()}
          >
            <input
              id="file-input"
              type="file"
              className="hidden"
              accept={ACCEPT_STRING}
              multiple
              onChange={(e) => handleUpload(e.target.files)}
            />
            {uploading ? (
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
            ) : (
              <Upload className="h-10 w-10 text-muted-foreground" />
            )}
            <p className="mt-4 text-sm font-medium">
              {uploading ? "Uploading..." : "Drop files here or click to browse"}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              PDF, DOCX, HTML, MD, TXT — up to 50 MB
            </p>
          </div>
          {uploadError && (
            <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              {uploadError}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Document List */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Your Documents</CardTitle>
            <CardDescription>{documents.length} document(s)</CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={fetchDocuments} className="gap-2">
            <RefreshCw className="h-4 w-4" /> Refresh
          </Button>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : documents.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <FileText className="h-12 w-12 text-muted-foreground/50" />
              <p className="mt-4 text-lg font-medium">No documents yet</p>
              <p className="text-sm text-muted-foreground">
                Upload your first document to get started.
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Format</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Chunks</TableHead>
                  <TableHead>Uploaded</TableHead>
                  <TableHead className="w-[80px]" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        {getMimeIcon(doc.mime_type)}
                        {doc.filename}
                      </div>
                    </TableCell>
                    <TableCell>
                      {doc.mime_type.includes("pdf")
                        ? "PDF"
                        : doc.mime_type.includes("word") || doc.mime_type.includes("docx")
                          ? "DOCX"
                          : doc.mime_type.includes("html")
                            ? "HTML"
                            : doc.mime_type === "text/plain"
                              ? "TXT"
                              : "MD"}
                    </TableCell>
                    <TableCell>{getStatusBadge(doc.status)}</TableCell>
                    <TableCell>
                      {doc.status === "ready"
                        ? (doc.metadata as Record<string, number>)?.chunk_count ?? "—"
                        : "—"}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setDeleteTarget(doc)}
                        className="text-muted-foreground hover:text-destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Document</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <strong>{deleteTarget?.filename}</strong>?
              This will permanently remove the document and all its chunks.
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
