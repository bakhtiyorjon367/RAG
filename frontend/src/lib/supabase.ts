import { createClient } from "@supabase/supabase-js"
import { setAccessToken } from "./auth-token"

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error("Missing Supabase environment variables")
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

supabase.auth.onAuthStateChange((_event, session) => {
  setAccessToken(session?.access_token ?? null)
})

void supabase.auth.getSession().then(({ data: { session } }) => {
  setAccessToken(session?.access_token ?? null)
})
