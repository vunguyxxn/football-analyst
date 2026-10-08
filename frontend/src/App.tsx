import { useQuery } from "@tanstack/react-query"

type HealthResponse = {
  status: string
}

async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch("/api/health")

  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`)
  }

  return response.json() as Promise<HealthResponse>
}

function App() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    retry: false,
    refetchInterval: 5000,
  })

  const backendStatus = health.isPending
    ? "Đang kiểm tra…"
    : health.isError || health.data.status !== "ok"
      ? "Backend: lỗi"
      : "Backend: OK"

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-5 bg-background px-6 text-center text-foreground">
      <h1 className="text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
        Hệ thống phân tích trận đấu bóng đá
      </h1>
      <p
        aria-live="polite"
        className={`rounded-full border px-4 py-2 text-sm font-medium ${
          backendStatus === "Backend: OK"
            ? "border-primary/40 bg-primary/10 text-primary"
            : "border-border bg-card text-muted-foreground"
        }`}
      >
        {backendStatus}
      </p>
    </main>
  )
}

export default App
