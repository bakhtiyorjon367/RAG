import { Link, useLocation } from "react-router-dom"
import { FileText, Search, MessageSquare, LogOut } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/hooks/useAuth"
import { cn } from "@/lib/utils"

const navItems = [
  { to: "/ingest", label: "Documents", icon: FileText },
  { to: "/search", label: "Search", icon: Search },
  { to: "/chat", label: "Chat", icon: MessageSquare },
]

const shellClass = "w-full px-4 sm:px-6 lg:px-8 xl:px-10"

export function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, signOut } = useAuth()
  const location = useLocation()

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className={cn(shellClass, "flex h-14 items-center justify-between")}>
          <div className="flex items-center gap-6">
            <Link to="/" className="flex items-center gap-2 font-semibold">
              <FileText className="h-5 w-5 text-primary" />
              <span>RAG Search</span>
            </Link>
            <nav className="flex items-center gap-1">
              {navItems.map((item) => {
                const Icon = item.icon
                const isActive =
                  item.to === "/chat"
                    ? location.pathname === "/chat"
                    : location.pathname.startsWith(item.to)
                return (
                  <Link key={item.to} to={item.to}>
                    <Button
                      variant={isActive ? "secondary" : "ghost"}
                      size="sm"
                      className={cn(
                        "gap-2",
                        isActive && "bg-secondary"
                      )}
                    >
                      <Icon className="h-4 w-4" />
                      {item.label}
                    </Button>
                  </Link>
                )
              })}
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">
              {user?.email}
            </span>
            <Button variant="ghost" size="sm" onClick={signOut} className="gap-2">
              <LogOut className="h-4 w-4" />
              Sign Out
            </Button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className={cn(shellClass, "py-6")}>{children}</main>
    </div>
  )
}
