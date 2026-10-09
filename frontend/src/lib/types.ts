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
