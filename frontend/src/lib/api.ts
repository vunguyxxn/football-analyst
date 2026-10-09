import type {
  Competition,
  HealthResponse,
  Match,
  PassNetwork,
} from "@/lib/types"

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path)
  if (!response.ok) {
    let message = `Yêu cầu thất bại (${response.status})`
    try {
      const body: unknown = await response.json()
      if (
        typeof body === "object" &&
        body !== null &&
        "detail" in body &&
        typeof body.detail === "string"
      ) {
        message = body.detail
      }
    } catch {
      message = `Máy chủ trả về lỗi ${response.status}`
    }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

export function fetchHealth(): Promise<HealthResponse> {
  return getJson<HealthResponse>("/api/health")
}

export function fetchCompetitions(): Promise<Competition[]> {
  return getJson<Competition[]>("/api/matches/competitions")
}

export function fetchMatches(
  competitionId: number,
  seasonId: number,
): Promise<Match[]> {
  const params = new URLSearchParams({
    competition_id: String(competitionId),
    season_id: String(seasonId),
  })
  return getJson<Match[]>(`/api/matches?${params.toString()}`)
}

export function fetchPassNetwork(
  matchId: number,
  team: string,
): Promise<PassNetwork> {
  const params = new URLSearchParams({ team })
  return getJson<PassNetwork>(
    `/api/matches/${matchId}/pass-network?${params.toString()}`,
  )
}
