import { Link } from "react-router-dom"
import {
  FileText,
  Info,
  AlertTriangle,
  ArrowRight,
  Server,
  Cpu,
  HardDrive,
  MemoryStick,
  Zap,
  Database,
  Layers,
  Search,
  MessageSquare,
  FileUp,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Progress } from "@/components/ui/progress"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { useAuth } from "@/hooks/useAuth"
import { cn } from "@/lib/utils"

const SUPPORTED_FORMATS = [
  {
    label: "PDF",
    extensions: ".pdf",
    mime: "application/pdf",
    package: "PyMuPDF + pymupdf4llm",
    packagePin: "pymupdf>=1.26.0",
    extraction: "Converted to markdown (preserves headings, tables, page metadata)",
  },
  {
    label: "Word",
    extensions: ".docx",
    mime: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    package: "python-docx",
    packagePin: "python-docx>=1.2.0",
    extraction: "Paragraph text joined; title/author from document properties",
  },
  {
    label: "HTML",
    extensions: ".html, .htm",
    mime: "text/html",
    package: "BeautifulSoup4 + lxml",
    packagePin: "beautifulsoup4>=4.14.0, lxml>=6.0.0",
    extraction: "Strips script/style/nav; plain text with line breaks",
  },
  {
    label: "Markdown",
    extensions: ".md",
    mime: "text/markdown, text/x-markdown",
    package: "— (stdlib)",
    packagePin: "UTF-8 decode",
    extraction: "Read as-is, no parsing library",
  },
  {
    label: "Plain text",
    extensions: ".txt",
    mime: "text/plain",
    package: "— (stdlib)",
    packagePin: "UTF-8 decode",
    extraction: "Read as-is, no parsing library",
  },
] as const

const shellClass = "w-full px-4 sm:px-6 lg:px-8 xl:px-10"

function FlowArrow({ className }: { className?: string }) {
  return (
    <div className={cn("flex shrink-0 items-center justify-center text-muted-foreground", className)}>
      <ArrowRight className="h-4 w-4" />
    </div>
  )
}

function FlowBox({
  title,
  subtitle,
  className,
}: {
  title: string
  subtitle?: string
  className?: string
}) {
  return (
    <div
      className={cn(
        "rounded-lg border bg-card px-3 py-2 text-center shadow-sm",
        className
      )}
    >
      <p className="text-xs font-semibold leading-tight">{title}</p>
      {subtitle && (
        <p className="mt-0.5 text-[10px] text-muted-foreground leading-tight">{subtitle}</p>
      )}
    </div>
  )
}

function StatGauge({
  label,
  value,
  detail,
  variant = "default",
}: {
  label: string
  value: number
  detail: string
  variant?: "default" | "danger" | "warning"
}) {
  const barClass =
    variant === "danger"
      ? "[&_[data-slot=progress-indicator]]:bg-destructive"
      : variant === "warning"
        ? "[&_[data-slot=progress-indicator]]:bg-amber-500"
        : ""

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span
          className={cn(
            "tabular-nums text-muted-foreground",
            variant === "danger" && "text-destructive font-medium",
            variant === "warning" && "text-amber-600 dark:text-amber-500 font-medium"
          )}
        >
          {value}%
        </span>
      </div>
      <Progress value={value} className={cn("h-2", barClass)} />
      <p className="text-xs text-muted-foreground">{detail}</p>
    </div>
  )
}

function StackGroup({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="mb-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">
        {title}
      </p>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item) => (
          <Badge key={item} variant="secondary" className="text-xs font-normal">
            {item}
          </Badge>
        ))}
      </div>
    </div>
  )
}

export default function About() {
  const { user } = useAuth()

  return (
    <div className="min-h-screen bg-background">
      {/* Public header */}
      <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className={cn(shellClass, "flex h-14 items-center justify-between")}>
          <Link to="/" className="flex items-center gap-2 font-semibold">
            <FileText className="h-5 w-5 text-primary" />
            <span>RAG Search</span>
          </Link>
          <div className="flex items-center gap-2">
            <Button variant="secondary" size="sm" className="gap-2" asChild>
              <Link to="/about">
                <Info className="h-4 w-4" />
                About
              </Link>
            </Button>
            {user ? (
              <Button size="sm" asChild>
                <Link to="/ingest">Documents</Link>
              </Button>
            ) : (
              <Button size="sm" asChild>
                <Link to="/login">Login</Link>
              </Button>
            )}
          </div>
        </div>
      </header>

      <main className={cn(shellClass, "py-8")}>
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">About This Application</h1>
          <p className="mt-2 text-muted-foreground max-w-3xl">
            Architecture overview, data pipeline, and current deployment constraints for
            the RAG Document Search Engine.
          </p>
        </div>

        <div className="grid gap-8 lg:grid-cols-3">
          {/* ── Left column (2/3) ── */}
          <div className="space-y-6 lg:col-span-2">
            {/* Tech stack */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Layers className="h-5 w-5 text-primary" />
                  Current Tech Stack
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <StackGroup
                  title="Frontend"
                  items={[
                    "React 19",
                    "Vite 7",
                    "Tailwind 4",
                    "shadcn / radix-ui",
                    "react-router 7",
                    "supabase-js",
                    "axios",
                  ]}
                />
                <Separator />
                <StackGroup
                  title="Backend"
                  items={[
                    "FastAPI",
                    "uvicorn",
                    "fastembed (ONNX)",
                    "FlashRank",
                    "google-genai",
                    "PyMuPDF4LLM",
                    "python-docx",
                    "BeautifulSoup4 / lxml",
                    "python-mecab-ko",
                  ]}
                />
                <Separator />
                <StackGroup
                  title="Data"
                  items={["Supabase Postgres", "pgvector (HNSW)", "Supabase Storage"]}
                />
                <Separator />
                <StackGroup title="LLM" items={["Google Gemini 2.5 Flash (free tier)"]} />
                <Separator />
                <StackGroup
                  title="Deploy"
                  items={["AWS EC2", "Docker", "nginx", "GHCR", "GitHub Actions"]}
                />
              </CardContent>
            </Card>

            {/* Supported upload formats & extraction */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <FileUp className="h-5 w-5 text-primary" />
                  Supported Upload Formats &amp; Extraction
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  Files accepted on the Documents (Ingest) page. Max upload size:{" "}
                  <strong>50 MB</strong> per file. Duplicate content (SHA-256 hash) is skipped per user.
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="overflow-x-auto rounded-lg border">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b bg-muted/50">
                        <th className="px-3 py-2 text-left font-medium">Format</th>
                        <th className="px-3 py-2 text-left font-medium">Extensions</th>
                        <th className="px-3 py-2 text-left font-medium hidden sm:table-cell">MIME type</th>
                        <th className="px-3 py-2 text-left font-medium">Extraction package</th>
                        <th className="px-3 py-2 text-left font-medium hidden md:table-cell">How text is extracted</th>
                      </tr>
                    </thead>
                    <tbody>
                      {SUPPORTED_FORMATS.map((fmt) => (
                        <tr key={fmt.label} className="border-b last:border-0">
                          <td className="px-3 py-2.5 font-medium">{fmt.label}</td>
                          <td className="px-3 py-2.5 text-muted-foreground font-mono">{fmt.extensions}</td>
                          <td className="px-3 py-2.5 text-muted-foreground hidden sm:table-cell">
                            <code className="text-[10px]">{fmt.mime}</code>
                          </td>
                          <td className="px-3 py-2.5">
                            <span className="font-medium">{fmt.package}</span>
                            {fmt.packagePin !== "UTF-8 decode" && (
                              <p className="mt-0.5 font-mono text-[10px] text-muted-foreground">{fmt.packagePin}</p>
                            )}
                          </td>
                          <td className="px-3 py-2.5 text-muted-foreground hidden md:table-cell">{fmt.extraction}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="rounded-md bg-muted/50 p-3 text-xs text-muted-foreground">
                  <p className="font-medium text-foreground mb-1">Document extraction libraries (requirements.txt)</p>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {[
                      "pymupdf>=1.26.0",
                      "pymupdf4llm (PDF→markdown)",
                      "python-docx>=1.2.0",
                      "beautifulsoup4>=4.14.0",
                      "lxml>=6.0.0",
                    ].map((pkg) => (
                      <Badge key={pkg} variant="outline" className="text-[10px] font-mono font-normal">
                        {pkg}
                      </Badge>
                    ))}
                  </div>
                  <p className="mt-2">
                    All extractors are lightweight — no PyTorch or GPU required. After extraction, text
                    flows into the chunking → embedding → storage pipeline described below.
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Full architecture overview */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Server className="h-5 w-5 text-primary" />
                  Application Architecture
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="rounded-lg border bg-muted/30 p-4">
                  <div className="flex flex-col items-stretch gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:justify-center">
                    <FlowBox title="Browser" subtitle="React SPA" />
                    <FlowArrow className="hidden sm:flex" />
                    <FlowBox title="nginx" subtitle=":8080 static + /api proxy" />
                    <FlowArrow className="hidden sm:flex" />
                    <FlowBox title="FastAPI" subtitle="Docker :8000" />
                    <FlowArrow className="hidden sm:flex" />
                    <FlowBox title="Supabase" subtitle="Auth + DB + Storage" />
                  </div>
                  <div className="mt-4 flex flex-col items-stretch gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:justify-center">
                    <FlowBox title="Gemini API" subtitle="LLM generation" className="border-dashed" />
                    <span className="hidden text-xs text-muted-foreground sm:inline">← called by FastAPI at chat time</span>
                  </div>
                  <p className="mt-4 text-xs text-muted-foreground text-center">
                    Frontend is built by GitHub Actions and served from{" "}
                    <code className="rounded bg-muted px-1">/var/www/rag-frontend</code>.
                    Backend image is pulled from GHCR and runs as{" "}
                    <code className="rounded bg-muted px-1">rag-backend</code> container on EC2.
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Ingestion pipeline */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Database className="h-5 w-5 text-primary" />
                  Ingestion Pipeline
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="overflow-x-auto pb-2">
                  <div className="flex min-w-max items-center gap-2">
                    <FlowBox title="Upload" subtitle="PDF, DOCX, HTML, MD, TXT" />
                    <FlowArrow />
                    <FlowBox title="Extract" subtitle="PyMuPDF4LLM / docx / BS4" />
                    <FlowArrow />
                    <FlowBox title="Chunk" subtitle="512 chars / 50 overlap" />
                    <FlowArrow />
                    <FlowBox title="Embed" subtitle="e5-base 768-dim ONNX" />
                    <FlowArrow />
                    <FlowBox title="Store" subtitle="Postgres + pgvector" />
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 text-sm">
                  <div className="rounded-md border p-3">
                    <p className="font-medium text-xs mb-1">Extraction libraries</p>
                    <ul className="text-xs text-muted-foreground space-y-1 list-disc list-inside">
                      <li>PDF → markdown via PyMuPDF4LLM</li>
                      <li>DOCX via python-docx</li>
                      <li>HTML via BeautifulSoup4 + lxml</li>
                      <li>Markdown / plain text read as UTF-8</li>
                    </ul>
                  </div>
                  <div className="rounded-md border p-3">
                    <p className="font-medium text-xs mb-1">Chunking engine</p>
                    <ul className="text-xs text-muted-foreground space-y-1 list-disc list-inside">
                      <li>Recursive character splitter (custom)</li>
                      <li>Separators: <code className="text-[10px]">\n\n, \n, ". ", " "</code></li>
                      <li>CHUNK_SIZE=512, CHUNK_OVERLAP=50 characters</li>
                      <li>MeCab-ko normalization for Korean FTS</li>
                    </ul>
                  </div>
                  <div className="rounded-md border p-3 sm:col-span-2">
                    <p className="font-medium text-xs mb-1">Embedding model-engine</p>
                    <ul className="text-xs text-muted-foreground space-y-1 list-disc list-inside">
                      <li>
                        <code className="text-[10px]">intfloat/multilingual-e5-base</code> — 768 dimensions, ONNX via fastembed
                      </li>
                      <li>Quantized QInt8 model (~280 MB) baked into Docker image</li>
                      <li>
                        E5 prefixes: <code className="text-[10px]">passage:</code> for chunks,{" "}
                        <code className="text-[10px]">query:</code> for search queries
                      </li>
                      <li>No PyTorch — ONNX Runtime only (CPU-friendly)</li>
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Storage */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <HardDrive className="h-5 w-5 text-primary" />
                  Data Storage (Text + pgvector)
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-lg border p-4 space-y-2">
                    <p className="font-semibold text-sm">documents table</p>
                    <ul className="text-xs text-muted-foreground space-y-1">
                      <li>filename, mime_type, status, content_hash</li>
                      <li>SHA-256 deduplication per user</li>
                      <li>Raw file in Supabase Storage bucket</li>
                      <li>Row Level Security by user_id</li>
                    </ul>
                  </div>
                  <div className="rounded-lg border p-4 space-y-2">
                    <p className="font-semibold text-sm">chunks table</p>
                    <ul className="text-xs text-muted-foreground space-y-1">
                      <li>
                        <code className="text-[10px]">content</code> TEXT — original chunk text
                      </li>
                      <li>
                        <code className="text-[10px]">content_normalized</code> — MeCab-ko for Korean FTS
                      </li>
                      <li>
                        <code className="text-[10px]">embedding vector(768)</code> — pgvector
                      </li>
                      <li>chunk_index, token_count, metadata JSONB</li>
                    </ul>
                  </div>
                </div>
                <div className="rounded-md bg-muted/50 p-3 text-xs text-muted-foreground">
                  <p className="font-medium text-foreground mb-1">Indexes</p>
                  <p>
                    HNSW on <code>embedding</code> (vector_cosine_ops, m=16, ef_construction=64) for
                    semantic search · GIN on{" "}
                    <code>to_tsvector(&apos;simple&apos;, content_normalized)</code> for keyword search
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Retrieval pipeline */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Search className="h-5 w-5 text-primary" />
                  Search &amp; Chat Pipeline
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="overflow-x-auto pb-2">
                  <div className="flex min-w-max flex-col gap-3">
                    <div className="flex items-center gap-2">
                      <FlowBox title="Query" subtitle="user question" />
                      <FlowArrow />
                      <FlowBox title="Embed" subtitle="query: prefix" />
                      <FlowArrow />
                      <div className="flex flex-col gap-2 rounded-lg border border-dashed p-2">
                        <FlowBox title="Vector Search" subtitle="match_chunks RPC" />
                        <FlowBox title="Keyword Search" subtitle="keyword_search_chunks RPC" />
                      </div>
                    </div>
                    <div className="flex items-center gap-2 pl-[calc(50%-8rem)]">
                      <FlowArrow />
                      <FlowBox title="RRF Fusion" subtitle="k=60" />
                      <FlowArrow />
                      <FlowBox title="Rerank" subtitle="FlashRank / Jina" />
                      <FlowArrow />
                      <FlowBox title="Gemini" subtitle="SSE stream" />
                    </div>
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 text-sm">
                  <div className="rounded-md border p-3">
                    <p className="font-medium text-xs mb-1">Vector search (pgvector)</p>
                    <ul className="text-xs text-muted-foreground space-y-1 list-disc list-inside">
                      <li>Cosine similarity via HNSW index</li>
                      <li>Threshold: 0.6 minimum similarity</li>
                      <li>Top 20 candidates before fusion</li>
                    </ul>
                  </div>
                  <div className="rounded-md border p-3">
                    <p className="font-medium text-xs mb-1">Keyword search (FTS)</p>
                    <ul className="text-xs text-muted-foreground space-y-1 list-disc list-inside">
                      <li>PostgreSQL tsvector + plainto_tsquery</li>
                      <li>MeCab-ko normalized query for Korean</li>
                      <li>Top 20 candidates before fusion</li>
                    </ul>
                  </div>
                  <div className="rounded-md border p-3">
                    <p className="font-medium text-xs mb-1">RRF fusion</p>
                    <ul className="text-xs text-muted-foreground space-y-1 list-disc list-inside">
                      <li>
                        score = Σ 1/(60 + rank) across vector + keyword lists
                      </li>
                      <li>Merges duplicate chunks, keeps max similarity</li>
                    </ul>
                  </div>
                  <div className="rounded-md border p-3">
                    <p className="font-medium text-xs mb-1">Rerank model-engine</p>
                    <ul className="text-xs text-muted-foreground space-y-1 list-disc list-inside">
                      <li>
                        FlashRank:{" "}
                        <code className="text-[10px]">jina-reranker-v2-base-multilingual</code>
                      </li>
                      <li>Sigmoid-normalized scores, threshold 0.5</li>
                      <li>Max 3 chunks per document in results</li>
                    </ul>
                  </div>
                </div>

                <div className="rounded-md border p-3 flex items-start gap-2">
                  <MessageSquare className="h-4 w-4 mt-0.5 text-primary shrink-0" />
                  <div className="text-xs text-muted-foreground">
                    <p className="font-medium text-foreground mb-1">Chat (RAG generation)</p>
                    <p>
                      Top-k chunks are sent as context to Gemini 2.5 Flash via google-genai SDK.
                      Response streams over Server-Sent Events (SSE). Search page returns chunks only
                      (no LLM).
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Gemini free tier warning */}
            <Alert className="border-amber-500/50 bg-amber-500/5">
              <AlertTriangle className="text-amber-600 dark:text-amber-500" />
              <AlertTitle>Gemini Free Tier Limits</AlertTitle>
              <AlertDescription>
                <p>
                  The app uses Google Gemini 2.5 Flash on the{" "}
                  <strong>free tier</strong> (AI Studio API key). Free tier enforces per-minute
                  request limits, daily quotas, and token caps. After sustained use, requests return{" "}
                  <code className="rounded bg-muted px-1 text-xs">429 Resource Exhausted</code> and
                  chat generation stops until the quota resets or you upgrade to a paid plan.
                </p>
                <p className="mt-2">
                  Search (chunk-only) still works without Gemini; only the Chat page requires the LLM.
                </p>
              </AlertDescription>
            </Alert>
          </div>

          {/* ── Right column (1/3) ── */}
          <div className="space-y-6">
            {/* AWS server stats */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Server className="h-5 w-5 text-primary" />
                  AWS EC2 Server Stats
                </CardTitle>
                <p className="text-xs text-muted-foreground">
                  Snapshot from production host (ip-172-31-25-163)
                </p>
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="flex items-start gap-3 rounded-md border p-3">
                  <Cpu className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
                  <div className="text-xs">
                    <p className="font-medium">CPU</p>
                    <p className="text-muted-foreground mt-0.5">
                      1 vCPU · Intel Xeon Platinum 8259CL @ 2.50 GHz · x86_64 · no GPU
                    </p>
                  </div>
                </div>

                <StatGauge
                  label="RAM"
                  value={68}
                  detail="3.8 GiB total · 2.6 GiB used · ~901 MiB available"
                  variant="warning"
                />

                <StatGauge
                  label="Swap"
                  value={60}
                  detail="2.0 GiB total · 1.2 GiB used — indicates memory pressure"
                  variant="warning"
                />

                <StatGauge
                  label="Disk (/)"
                  value={93}
                  detail="28 GB total · 26 GB used · 2.2 GB free"
                  variant="danger"
                />

                <Alert variant="destructive" className="py-3">
                  <AlertTriangle />
                  <AlertDescription className="text-xs">
                    Deploy workflow warns when free disk &lt; 3 GB. Current 2.2 GB free blocks
                    pulling larger Docker images or caching bigger ONNX models.
                  </AlertDescription>
                </Alert>
              </CardContent>
            </Card>

            {/* Bottlenecks */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <MemoryStick className="h-5 w-5 text-primary" />
                  Current Bottlenecks
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3 text-sm">
                  <li className="flex gap-2">
                    <span className="text-destructive font-bold shrink-0">•</span>
                    <span>
                      <strong>RAM + swap pressure</strong> — e5-base (~280 MB) + FlashRank reranker
                      already consume most of 3.8 GiB. Cannot load e5-large, BGE-M3, or a local LLM.
                    </span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-amber-600 dark:text-amber-500 font-bold shrink-0">•</span>
                    <span>
                      <strong>Single vCPU, no GPU</strong> — ONNX embedding and reranking run on CPU
                      only; inference latency is the floor with no batching headroom.
                    </span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-destructive font-bold shrink-0">•</span>
                    <span>
                      <strong>Disk 93% full</strong> — cannot store larger model caches, Docker layers,
                      or expand fastembed cache without EBS resize.
                    </span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-muted-foreground font-bold shrink-0">•</span>
                    <span>
                      <strong>Gemini free tier</strong> — rate limits block sustained chat usage;
                      no fallback LLM on-server.
                    </span>
                  </li>
                </ul>
              </CardContent>
            </Card>

            {/* Upgrade recommendations */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Zap className="h-5 w-5 text-primary" />
                  Upgrade Recommendations
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <div>
                  <p className="font-medium mb-2">Infrastructure</p>
                  <ul className="text-xs text-muted-foreground space-y-1.5 list-disc list-inside">
                    <li>Resize EBS volume to ≥ 50 GB (immediate — fixes deploy failures)</li>
                    <li>Upgrade to t3.medium (2 vCPU, 4 GiB) or t3.large (2 vCPU, 8 GiB) for headroom</li>
                    <li>For local LLM: g4dn.xlarge (GPU) or use external API only</li>
                    <li>Add swap only as temporary relief; RAM upgrade is the real fix</li>
                  </ul>
                </div>
                <Separator />
                <div>
                  <p className="font-medium mb-2">Models (when infra allows)</p>
                  <ul className="text-xs text-muted-foreground space-y-1.5 list-disc list-inside">
                    <li>
                      <strong>Embedding:</strong> e5-large (1024-dim) or BGE-M3 — needs ~8 GiB RAM +
                      migration 005-style schema change
                    </li>
                    <li>
                      <strong>Reranker:</strong> cross-encoder with GPU or Cohere/Voyage API rerank
                    </li>
                    <li>
                      <strong>LLM:</strong> Gemini paid tier, or self-hosted Llama/Mistral on GPU instance
                    </li>
                  </ul>
                </div>
                <Separator />
                <div>
                  <p className="font-medium mb-2">Packages to review / update</p>
                  <div className="space-y-2 text-xs">
                    <p className="text-muted-foreground font-medium">Backend (requirements.txt)</p>
                    <div className="flex flex-wrap gap-1">
                      {[
                        "fastapi==0.115.12",
                        "fastembed>=0.7.0",
                        "flashrank>=0.2.0",
                        "google-genai>=1.0.0",
                        "supabase==2.28.0",
                        "pymupdf>=1.26.0",
                      ].map((pkg) => (
                        <Badge key={pkg} variant="outline" className="text-[10px] font-mono">
                          {pkg}
                        </Badge>
                      ))}
                    </div>
                    <p className="text-muted-foreground font-medium mt-2">Frontend (package.json)</p>
                    <div className="flex flex-wrap gap-1">
                      {[
                        "react ^19.2.0",
                        "vite ^7.3.1",
                        "@supabase/supabase-js ^2.95.3",
                        "axios ^1.13.5",
                      ].map((pkg) => (
                        <Badge key={pkg} variant="outline" className="text-[10px] font-mono">
                          {pkg}
                        </Badge>
                      ))}
                    </div>
                    <p className="text-muted-foreground mt-2">
                      Bump fastembed / flashrank when upgrading embed or rerank models. Pin google-genai
                      when switching Gemini models or API versions.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  )
}
