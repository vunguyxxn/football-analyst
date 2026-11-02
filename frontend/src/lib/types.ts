export type Competition = {
  competition_id: number
  season_id: number
  competition_name: string
  season_name: string
  country_name: string | null
}

export type Match = {
  match_id: number
  match_date: string | null
  kick_off: string | null
  home_team: string
  away_team: string
  home_score: number | null
  away_score: number | null
  competition_stage: string | null
}

export type PassNetworkNode = {
  player: string
  short_name: string
  avg_x_m: number
  avg_y_m: number
  pass_count: number
  touches: number
}

export type PassNetworkEdge = {
  source: string
  target: string
  count: number
}

export type PassNetwork = {
  nodes: PassNetworkNode[]
  edges: PassNetworkEdge[]
}

export type HealthResponse = {
  status: string
}

export type MetricItem = {
  key: string
  label: string
  value: number | string
  unit: string | null
  scope: "team" | "player" | "match"
  subject: string | null
}

export type AnalysisResult = { source: "video" | "statsbomb"; metrics: MetricItem[] }

export type MetricDefinition = {
  key: string
  version: number
  label: string
  unit: string | null
  source: "statsbomb" | "video"
  implementation: "computed" | "documented"
  mapping: "same-provider" | "approximation" | "project"
  formula: string
  required_columns: string[]
  interpretation: string
  caveats: string[]
  source_url: string
  reference_url: string
}

export type TrackingRow = {
  frame: number
  time_s: number
  track_id: number
  team: "A" | "B" | "referee" | "unknown"
  x_m: number
  y_m: number
}
