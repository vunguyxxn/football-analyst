export const MAX_PROFILE_BYTES = 5 * 1024 * 1024
export type RoleContext = { status: "reference" | "unknown"; position: string | null; shape: string | null; count: number; first: number; last: number }
export type EventStats = { passes: number; completed: number | null; completionPct: number | null; carries: number; shots: number; goals: number | null; events: number; indices: Record<"Pass" | "Carry" | "Shot", number[]>; roles: RoleContext[] }
export type TrackingStats = { samples: number; coverage: number; represented: number; representedFraction: number; distance: number; meanSpeed: number | null; maxSpeed: number | null; rejected: number; heatmap: number[][]; median: [number, number] | null }
export type PlayerProfile = { key: string; id: number; name: string; shortName: string; team: string; jersey: number | null; starter: boolean | null; goalkeeper: boolean | null; events: EventStats | null; tracking: TrackingStats | null }
export type PlayerReport = { source: "statsbomb" | "metrica"; label: string; scope: string; players: PlayerProfile[]; teams: string[] }

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Cấu trúc hồ sơ không hợp lệ.")
  return value as Record<string, unknown>
}
function text(value: unknown): string {
  if (typeof value !== "string" || !value.trim()) throw new Error("Hồ sơ thiếu tên hoặc nhãn nguồn.")
  return value
}
function number(value: unknown, min = 0, max = Infinity): number {
  if (typeof value !== "number" || !Number.isFinite(value) || value < min || value > max) throw new Error("Chỉ số trong hồ sơ không hợp lệ.")
  return value
}
function integer(value: unknown, min = 0): number {
  const result = number(value, min)
  if (!Number.isSafeInteger(result)) throw new Error("ID hoặc số đếm trong hồ sơ không hợp lệ.")
  return result
}
function nullable(value: unknown, parse: (value: unknown) => number): number | null { return value === null ? null : parse(value) }
function boolean(value: unknown): boolean { if (typeof value !== "boolean") throw new Error("Cờ trạng thái hồ sơ không hợp lệ."); return value }
function array(value: unknown): unknown[] { if (!Array.isArray(value)) throw new Error("Danh sách trong hồ sơ không hợp lệ."); return value }

export function parsePlayerReport(content: string): PlayerReport {
  if (new TextEncoder().encode(content).length > MAX_PROFILE_BYTES) throw new Error("File hồ sơ vượt giới hạn 5 MB.")
  let raw: unknown
  try { raw = JSON.parse(content.replace(/^\uFEFF/, "")) } catch { throw new Error("File hồ sơ không phải JSON hợp lệ.") }
  const data = object(raw)
  let report: PlayerReport
  if (data.kind === "statsbomb_player_profiles_v1" && data.source === "statsbomb") {
    const match = integer(data.match_id, 1), ids = new Set<number>()
    const ownedEvents = new Set<number>()
    const players = array(data.players).map(value => {
      const p = object(value), id = integer(p.player_id, 1)
      if (integer(p.match_id, 1) !== match || ids.has(id)) throw new Error("Hồ sơ trùng player ID hoặc lẫn trận đấu.")
      ids.add(id)
      const passes = integer(p.passes_attempted), completed = nullable(p.passes_completed, v => integer(v))
      const carries = integer(p.carries), shots = integer(p.shots), goals = nullable(p.shot_goals, v => integer(v))
      const completionPct = nullable(p.pass_completion_pct, v => number(v, 0, 100))
      const expectedPct = completed !== null && passes ? completed / passes * 100 : null
      if ((completed !== null && completed > passes) || (goals !== null && goals > shots) ||
        (expectedPct === null ? completionPct !== null : completionPct === null || Math.abs(expectedPct - completionPct) > 1e-5)) throw new Error("Tổng hoặc tỷ lệ sự kiện không khớp.")
      const sourceIndices = object(p.event_indices)
      const indices = {} as EventStats["indices"]
      for (const [key, count] of [["Pass", passes], ["Carry", carries], ["Shot", shots]] as const) {
        indices[key] = array(sourceIndices[key]).map(v => integer(v, 1))
        if (indices[key].length !== count) throw new Error("Số index sự kiện không khớp thống kê.")
        for (const index of indices[key]) {
          if (ownedEvents.has(index)) throw new Error("Một sự kiện bị gán nhiều lần hoặc nhiều cầu thủ.")
          ownedEvents.add(index)
        }
      }
      const roles = array(p.role_contexts).map(value => {
        const role = object(value)
        if (role.status !== "reference" && role.status !== "unknown") throw new Error("Trạng thái vai trò không hợp lệ.")
        const first = integer(role.first_event_index, 1), last = integer(role.last_event_index, first)
        return { status: role.status, position: role.status === "reference" ? text(object(role.position).name) : null,
          shape: role.status === "reference" ? text(role.shape) : null, count: integer(role.event_count), first, last } as RoleContext
      })
      const events = integer(p.recorded_player_events)
      if (roles.reduce((sum, role) => sum + role.count, 0) !== events || passes + carries + shots > events) throw new Error("Số sự kiện và ngữ cảnh vai trò không khớp.")
      return { key: `statsbomb:${match}:${id}`, id, name: text(p.player), shortName: text(p.short_name), team: text(p.team),
        jersey: nullable(p.jersey_number, v => integer(v)), starter: boolean(p.starter), goalkeeper: null,
        events: { passes, completed, completionPct, carries, shots, goals, events, indices, roles }, tracking: null } as PlayerProfile
    })
    report = { source: "statsbomb", label: `StatsBomb · Trận ${match}`, scope: "Sự kiện ghi nhận trong trận · hiệp 1–4", players, teams: [] }
  } else if (data.kind === "offline_metrica_tactics_v1") {
    if (data.coordinate_system !== "105x68_bottom_left") throw new Error("Hệ tọa độ tracking không được hỗ trợ.")
    const game = integer(data.game, 1), period = integer(data.period, 1), start = number(data.start_s), stop = number(data.stop_s, start)
    if (period > 2 || stop <= start) throw new Error("Khoảng tracking không hợp lệ.")
    const heatmap = object(data.heatmap)
    if (heatmap.columns !== 21 || heatmap.rows !== 14 || heatmap.origin !== "bottom_left" || heatmap.unit !== "observed_frames") throw new Error("Định dạng heatmap không được hỗ trợ.")
    const policy = object(data.motion_policy), maxSpeed = number(policy.max_speed_kmh, 0, 40)
    const ids = new Set<number>(), teams = new Set<string>()
    const players = array(data.teams).flatMap(value => {
      const team = object(value), name = text(team.team)
      if (teams.has(name)) throw new Error("Trùng đội trong báo cáo tracking.")
      teams.add(name)
      return array(team.players).map(value => {
        const p = object(value), id = integer(p.track_id, 1)
        if (ids.has(id) || p.team !== name) throw new Error("Trùng ID hoặc lẫn đội tracking.")
        ids.add(id)
        const samples = integer(p.samples), coverage = number(p.sample_coverage, 0, 1)
        const represented = number(p.represented_motion_duration_s, 0, stop - start + 1e-6)
        const representedFraction = number(p.represented_window_fraction, 0, 1)
        const distance = number(p.observed_distance_m), mean = nullable(p.mean_speed_kmh, v => number(v, 0, maxSpeed)), maximum = nullable(p.max_speed_kmh, v => number(v, 0, maxSpeed))
        if (Math.abs(represented / (stop - start) - representedFraction) > 1e-5 ||
          (represented === 0 ? mean !== null || maximum !== null || distance !== 0 : mean === null || maximum === null || Math.abs(distance / represented * 3.6 - mean) > 1e-5 || mean > maximum + 1e-6)) throw new Error("Chỉ số chuyển động hoặc thời gian đại diện không khớp.")
        const grid = array(p.heatmap_observed_frames).map(row => array(row).map(v => integer(v)))
        if (grid.length !== 14 || grid.some(row => row.length !== 21) || grid.flat().reduce((a, b) => a + b, 0) !== samples) throw new Error("Heatmap không khớp số mẫu quan sát.")
        const position = p.median_position_m === null ? null : array(p.median_position_m)
        if (position && position.length !== 2) throw new Error("Vị trí trung vị không hợp lệ.")
        const median: [number, number] | null = position ? [number(position[0], 0, 105), number(position[1], 0, 68)] : null
        return { key: `metrica:${game}:${period}:${start}:${stop}:${name}:${id}`, id, name: `Cầu thủ ID ${id}`, shortName: `ID ${id}`, team: name,
          jersey: null, starter: null, goalkeeper: boolean(p.is_goalkeeper), events: null,
          tracking: { samples, coverage, represented, representedFraction, distance, meanSpeed: mean, maxSpeed: maximum,
            rejected: integer(p.rejected_motion_intervals), heatmap: grid, median } } as PlayerProfile
      })
    })
    report = { source: "metrica", label: `Metrica · Game ${game}`, scope: `Hiệp ${period} · giây ${start}–${stop} · ${stop - start} giây`, players, teams: [] }
  } else throw new Error("Chọn báo cáo hồ sơ StatsBomb hoặc Metrica đã xử lý.")
  if (report.players.length > 1000) throw new Error("Báo cáo vượt 1.000 hồ sơ.")
  report.teams = [...new Set(report.players.map(p => p.team))].sort((a, b) => a.localeCompare(b))
  return report
}

export function filterPlayers(report: PlayerReport, team: string, search: string): PlayerProfile[] {
  const query = search.trim().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d").replace(/Đ/g, "D").toLocaleLowerCase()
  return report.players.filter(p => (team === "" || p.team === team) && `${p.name} ${p.shortName} ${p.id}`.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d").replace(/Đ/g, "D").toLocaleLowerCase().includes(query))
    .sort((a, b) => report.source === "metrica" ? a.team.localeCompare(b.team) || a.id - b.id : Number(b.starter) - Number(a.starter) || a.name.localeCompare(b.name) || a.id - b.id)
}

export function formatProfileMetric(value: number | null, digits = 0): string {
  return value === null ? "—" : new Intl.NumberFormat("vi-VN", { maximumFractionDigits: digits }).format(value)
}
