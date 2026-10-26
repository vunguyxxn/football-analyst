export const MAX_COACH_BYTES = 10 * 1024 * 1024
export const COACH_FEATURES = ["distance_m", "angle_rad", "lateral_m", "is_header", "is_other_body", "is_free_kick", "first_time", "under_pressure"] as const
export type CoachFeature = typeof COACH_FEATURES[number]
export const COACH_LABELS: Record<CoachFeature, string> = { distance_m: "Khoảng cách (m)", angle_rad: "Góc mở (rad)", lateral_m: "Lệch ngang (m)", is_header: "Đánh đầu (0/1)", is_other_body: "Bộ phận khác (0/1)", is_free_kick: "Sút phạt trực tiếp (0/1)", first_time: "First time (0/1)", under_pressure: "Dưới áp lực (0/1)" }
export type FeatureValues = Record<CoachFeature, number>
export type CoachShot = { id: string; index: number; teamId: number; playerId: number | null; player: string; shortName: string; period: number; minute: number | null; second: number | null; xg: number; margin: number; base: number; features: FeatureValues; shap: FeatureValues }
export type CoachCard = { id: string; rule: string; criterion: string; title: string; action: string; interpretation: string; shots: CoachShot[]; fraction: number; meanXg: number; meanFeatures: FeatureValues; meanShap: FeatureValues; support: CoachFeature[] }
export type CoachTeam = { id: number; name: string; status: string; shots: CoachShot[]; totalXg: number; meanXg: number | null; cards: CoachCard[] }
export type CoachReport = { matchId: number; teams: CoachTeam[]; shots: CoachShot[]; split: string | null; modelHash: string; trees: number; limitations: string[]; original: Record<string, unknown> }

function fail(message = "Báo cáo HLV không hợp lệ."): never { throw new Error(message) }
function obj(value: unknown): Record<string, unknown> { return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : fail() }
function list(value: unknown): unknown[] { return Array.isArray(value) ? value : fail() }
function str(value: unknown): string { return typeof value === "string" && value.trim() ? value : fail() }
function num(value: unknown, min = -Infinity, max = Infinity): number { return typeof value === "number" && Number.isFinite(value) && value >= min && value <= max ? value : fail("Báo cáo có chỉ số không hợp lệ.") }
function int(value: unknown, min = 0): number { const n = num(value, min); return Number.isSafeInteger(n) ? n : fail() }
function optionalInt(value: unknown): number | null { return value === null ? null : int(value) }
function equal(a: number, b: number, tolerance = 1e-6) { if (Math.abs(a - b) > tolerance) fail("Số liệu hoặc căn cứ của báo cáo không khớp.") }
function values(value: unknown): FeatureValues { const data = obj(value); return Object.fromEntries(COACH_FEATURES.map(key => [key, num(data[key])])) as FeatureValues }
function average(rows: CoachShot[], field: "features" | "shap", key: CoachFeature): number { return rows.reduce((sum, row) => sum + row[field][key], 0) / rows.length }
function sameIds(a: string[], b: string[]) { const expected = new Set(b); return a.length === b.length && new Set(a).size === a.length && a.every(id => expected.has(id)) }

export function parseCoachReport(content: string): CoachReport {
  if (new TextEncoder().encode(content).length > MAX_COACH_BYTES) fail("File báo cáo vượt giới hạn 10 MB.")
  let raw: unknown
  try { raw = JSON.parse(content.replace(/^\uFEFF/, "")) } catch { fail("Không đọc được JSON báo cáo.") }
  const data = obj(raw)
  if (data.kind !== "shot_advisor_v1" || data.source !== "statsbomb" || data.timing !== "post_match") fail("Chọn báo cáo advisor sau trận từ StatsBomb đã xử lý.")
  const matchId = int(data.match_id, 1), audit = obj(data.model_audit), protocol = obj(data.protocol)
  if (audit.units !== "log_odds" || audit.method !== "TreeExplainer/tree_path_dependent") fail("Đơn vị hoặc phương pháp SHAP không được hỗ trợ.")
  const trees = int(audit.trees_explained, 1)
  if (trees !== int(audit.best_iteration) + 1) fail("Số cây SHAP không khớp mô hình dự đoán.")
  const modelHash = str(audit.model_sha256)
  if (!/^[a-f0-9]{64}$/.test(modelHash)) fail("Thiếu hash mô hình hợp lệ.")
  const seenIds = new Set<string>(), seenIndices = new Set<number>()
  const sourceShots = list(data.shots)
  if (sourceShots.length > 10_000) fail("Báo cáo vượt 10.000 cú sút.")
  const shots = sourceShots.map(value => {
    const s = obj(value), id = str(s.event_id), index = int(s.event_index, 1)
    if (seenIds.has(id) || seenIndices.has(index)) fail("Trùng event ID hoặc index cú sút.")
    seenIds.add(id); seenIndices.add(index)
    const features = values(s.features), shap = values(s.shap_log_odds)
    num(features.distance_m, 0); num(features.angle_rad, 0, Math.PI); num(features.lateral_m, 0, 34)
    for (const key of COACH_FEATURES.slice(3)) if (features[key] !== 0 && features[key] !== 1) fail("Cờ feature cú sút phải là 0 hoặc 1.")
    const base = num(s.base_log_odds), margin = num(s.margin), xg = num(s.xg, 0, 1)
    const restored = base + COACH_FEATURES.reduce((sum, key) => sum + shap[key], 0)
    equal(margin, restored, 1e-5); equal(xg, 1 / (1 + Math.exp(-restored)), 1e-6)
    const period = int(s.period, 1)
    if (period > 4) fail("Báo cáo chứa cú sút ngoài hiệp 1–4.")
    const second = optionalInt(s.second)
    if (second !== null && second > 59) fail("Giây của cú sút không hợp lệ.")
    const player = s.player === null ? "Chưa rõ cầu thủ" : str(s.player)
    return { id, index, teamId: int(s.team_id, 1), playerId: s.player_id === null ? null : int(s.player_id, 1), player,
      shortName: s.short_name === null ? player : str(s.short_name), period, minute: optionalInt(s.minute), second, features, shap, base, margin, xg } as CoachShot
  }).sort((a, b) => a.index - b.index)
  if (shots.length) for (const shot of shots) equal(shot.base, shots[0].base, 1e-6)
  const minimumTeam = int(protocol.minimum_team_shots, 1), minimumSubset = int(protocol.minimum_subset_shots, 1)
  const low = num(protocol.low_xg_threshold, 0, 1), high = num(protocol.high_xg_threshold, low, 1)
  const lowFraction = num(protocol.low_xg_fraction, 0, 1), highFraction = num(protocol.high_xg_fraction, 0, 1), pressureFraction = num(protocol.pressure_fraction, 0, 1)
  const teamIds = new Set<number>(), cardIds = new Set<string>()
  const teams = list(data.teams).map(value => {
    const team = obj(value), id = int(team.team_id, 1), name = str(team.team), status = str(team.status)
    if (teamIds.has(id)) fail("Trùng ID đội trong báo cáo.")
    teamIds.add(id)
    const members = shots.filter(s => s.teamId === id), totalXg = num(team.xg_total, 0)
    if (int(team.eligible_shots) !== members.length) fail("Số cú sút của đội không khớp.")
    equal(totalXg, members.reduce((sum, s) => sum + s.xg, 0))
    const meanXg = team.mean_xg === null ? null : num(team.mean_xg, 0, 1)
    if (!members.length ? meanXg !== null : meanXg === null) fail("xG trung bình của đội thiếu hoặc không đúng phạm vi.")
    if (members.length) equal(meanXg!, totalXg / members.length)
    const membersById = new Map(members.map(s => [s.id, s])), rules = new Set<string>()
    const cards = list(team.recommendations).map(value => {
      const card = obj(value), cardId = str(card.id), rule = str(card.rule), facts = obj(card.evidence)
      if (cardIds.has(cardId)) fail("Trùng ID gợi ý.")
      if (rules.has(rule)) fail("Trùng luật gợi ý trong cùng đội.")
      rules.add(rule)
      cardIds.add(cardId)
      const ids = list(facts.event_ids).map(str), selected = ids.map(eventId => membersById.get(eventId) ?? fail("Căn cứ trỏ tới cú sút không tồn tại hoặc khác đội."))
      if (new Set(ids).size !== ids.length || selected.length < minimumSubset || members.length < minimumTeam || int(facts.subset_shots) !== selected.length || int(facts.team_shots) !== members.length) fail("Số lượng cú sút căn cứ không khớp.")
      const fraction = num(facts.fraction, 0, 1), mean = num(facts.mean_xg, 0, 1), meanFeatures = values(facts.mean_features), meanShap = values(facts.mean_shap_log_odds)
      equal(fraction, selected.length / members.length); equal(mean, selected.reduce((sum, s) => sum + s.xg, 0) / selected.length)
      for (const key of COACH_FEATURES) { equal(meanFeatures[key], average(selected, "features", key)); equal(meanShap[key], average(selected, "shap", key)) }
      const candidates = rule === "review_low_quality_shots" ? members.filter(s => s.xg < low) : rule === "review_good_entries" ? members.filter(s => s.xg >= high) : rule === "review_pressure_support" ? members.filter(s => s.features.under_pressure === 1) : fail("Luật gợi ý không được hỗ trợ.")
      const threshold = rule === "review_low_quality_shots" ? lowFraction : rule === "review_good_entries" ? highFraction : pressureFraction
      if (!sameIds(ids, candidates.map(s => s.id)) || fraction < threshold) fail("Cú sút căn cứ không đúng nhóm hoặc ngưỡng của luật.")
      const geometry = ["distance_m", "angle_rad", "lateral_m"] as CoachFeature[]
      const sign = rule === "review_good_entries" ? 1 : -1
      const expectedSupport = rule === "review_pressure_support" ? (meanShap.under_pressure < 0 ? ["under_pressure"] : []) : (sign * geometry.reduce((sum, key) => sum + meanShap[key], 0) > 0 ? geometry.filter(key => sign * meanShap[key] > 0) : [])
      const support = list(card.supporting_features).map(str)
      if (!expectedSupport.length || !sameIds(support, expectedSupport)) fail("SHAP không hỗ trợ diễn giải gợi ý.")
      const criterion = rule === "review_low_quality_shots" ? `Nhóm có xG < ${low.toLocaleString("vi-VN")}` : rule === "review_good_entries" ? `Nhóm có xG ≥ ${high.toLocaleString("vi-VN")}` : "Nhóm dứt điểm dưới áp lực"
      return { id: cardId, rule, criterion, title: str(card.title), action: str(card.action), interpretation: str(card.interpretation), shots: selected.sort((a, b) => a.index - b.index), fraction, meanXg: mean, meanFeatures, meanShap, support: support as CoachFeature[] } as CoachCard
    })
    if (cards.length ? status !== "review_suggestions" : status !== (members.length < minimumTeam ? "insufficient_data" : "no_rule_triggered")) fail("Trạng thái gợi ý không khớp dữ liệu.")
    return { id, name, status, shots: members, totalXg, meanXg, cards } as CoachTeam
  })
  if (teams.length > 2 || shots.some(s => !teamIds.has(s.teamId))) fail("Cú sút không thuộc hai đội của trận.")
  const provenance = data.provenance ? obj(data.provenance) : null
  const split = provenance?.model_dataset_split === undefined ? null : str(provenance.model_dataset_split)
  if (split && !["train", "val", "test"].includes(split)) fail("Phân tập nguồn không được hỗ trợ.")
  return { matchId, teams, shots, split, modelHash, trees, limitations: list(data.limitations).map(str), original: data }
}

export function coachTime(shot: CoachShot): string {
  return shot.minute === null || shot.second === null ? "—" : `${shot.minute}:${String(shot.second).padStart(2, "0")}`
}
