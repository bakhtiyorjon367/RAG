import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import { ThemeProvider } from "next-themes"
import { AuthProvider } from "@/hooks/useAuth"
import { ProtectedRoute } from "@/components/layout/ProtectedRoute"
import { AppLayout } from "@/components/layout/AppLayout"
import { Toaster } from "@/components/ui/sonner"
import Login from "@/pages/Login"
import Signup from "@/pages/Signup"
import About from "@/pages/About"
import Ingest from "@/pages/Ingest"
import Chat from "@/pages/Chat"
import Search from "@/pages/Search"

export default function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/about" element={<About />} />

            {/* Protected routes */}
            <Route
              path="/ingest"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <Ingest />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/chat"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <Chat />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/search"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <Search />
                  </AppLayout>
                </ProtectedRoute>
              }
            />

            {/* Default redirect */}
            <Route path="/" element={<Navigate to="/ingest" replace />} />
            <Route path="*" element={<Navigate to="/ingest" replace />} />
          </Routes>
          <Toaster />
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  )
}
