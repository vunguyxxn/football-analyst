import { parseCoachReport, type CoachReport } from "./coachReport.ts"

export const COACH_HISTORY_KEY = "football-analyst.coach-history.v1"
export const MAX_HISTORY_ENTRIES = 5
// UTF-16 budget below common localStorage limits; a large report still opens
// normally even when it cannot be kept in this convenience history.
export const MAX_HISTORY_BYTES = 2 * 1024 * 1024
type HistoryStorage = Pick<Storage, "getItem" | "setItem">
export type CoachHistoryEntry = { id: string; name: string; openedAt: string; matchId: number; teams: string[]; content: string }

export async function coachReportFingerprint(content: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(content))
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("")
}

function validDate(value: unknown): value is string {
  return typeof value === "string" && /^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value))
}

export function readCoachHistory(storage: HistoryStorage): CoachHistoryEntry[] {
  const raw = storage.getItem(COACH_HISTORY_KEY)
  if (!raw) return []
  if (raw.length * 2 > MAX_HISTORY_BYTES) throw new Error("Lịch sử vượt giới hạn lưu trữ; dữ liệu cũ được giữ nguyên.")
  let data: { version?: unknown; entries?: unknown }
  try { data = JSON.parse(raw) } catch { throw new Error("Lịch sử không đọc được; dữ liệu cũ được giữ nguyên.") }
  if (!data || data.version !== 1 || !Array.isArray(data.entries) || data.entries.length > MAX_HISTORY_ENTRIES) throw new Error("Định dạng lịch sử không được hỗ trợ.")
  const seen = new Set<string>()
  for (const entry of data.entries) {
    if (!entry || typeof entry.id !== "string" || !/^[a-f0-9]{64}$/.test(entry.id) || seen.has(entry.id)
      || typeof entry.name !== "string" || !entry.name.trim() || entry.name.length > 255 || !validDate(entry.openedAt)
      || !Number.isSafeInteger(entry.matchId) || entry.matchId < 1 || typeof entry.content !== "string"
      || !Array.isArray(entry.teams) || entry.teams.length > 2 || !entry.teams.every((name: unknown) => typeof name === "string" && name.trim())) {
      throw new Error("Lịch sử có mục không hợp lệ; dữ liệu cũ được giữ nguyên.")
    }
    seen.add(entry.id)
  }
  return data.entries as CoachHistoryEntry[]
}

export async function saveCoachHistory(storage: HistoryStorage, report: CoachReport, name: string, openedAt: string): Promise<CoachHistoryEntry[]> {
  if (!validDate(openedAt)) throw new Error("Thời điểm mở báo cáo không hợp lệ.")
  const content = JSON.stringify(report.original)
  const id = await coachReportFingerprint(content)
  const entry = { id, name: name.trim().slice(0, 255) || "Báo cáo JSON", openedAt, matchId: report.matchId, teams: report.teams.map(team => team.name), content }
  const serialize = (entries: CoachHistoryEntry[]) => JSON.stringify({ version: 1, entries })
  if (serialize([entry]).length * 2 > MAX_HISTORY_BYTES) throw new Error("Báo cáo đang mở quá lớn để lưu lịch sử 2 MB. Bạn vẫn có thể xem và tải JSON.")
  // Read after hashing to merge the latest storage state before synchronous write.
  const existing = readCoachHistory(storage)
  const previous = existing.find(item => item.id === id)
  const latest = previous && Date.parse(previous.openedAt) > Date.parse(openedAt) ? previous : entry
  const entries = [latest, ...existing.filter(item => item.id !== id)]
    .sort((a, b) => Date.parse(b.openedAt) - Date.parse(a.openedAt)).slice(0, MAX_HISTORY_ENTRIES)
  while (serialize(entries).length * 2 > MAX_HISTORY_BYTES) entries.pop()
  storage.setItem(COACH_HISTORY_KEY, serialize(entries))
  return entries
}

export async function restoreCoachHistory(entry: CoachHistoryEntry): Promise<CoachReport> {
  if (await coachReportFingerprint(entry.content) !== entry.id) throw new Error("Nội dung báo cáo đã thay đổi trong lịch sử; hãy mở lại JSON gốc.")
  const report = parseCoachReport(entry.content)
  if (report.matchId !== entry.matchId || JSON.stringify(report.teams.map(team => team.name)) !== JSON.stringify(entry.teams)) throw new Error("Thông tin lịch sử không khớp báo cáo gốc.")
  return report
}

export function coachProvenance(report: CoachReport) {
  const provenance = report.original.provenance
  const fields = provenance && typeof provenance === "object" && !Array.isArray(provenance) ? provenance as Record<string, unknown> : {}
  const hash = (value: unknown, length: number) => typeof value === "string" && new RegExp(`^[a-f0-9]{${length}}$`).test(value) ? value : null
  return {
    generatedAt: validDate(report.original.generated_at) ? report.original.generated_at : null,
    sourceRevision: hash(fields.source_revision, 40),
    eventsHash: hash(fields.events_sha256, 64),
  }
}

export function coachOpenedTime(value: string): string {
  return new Date(value).toLocaleString("vi-VN", { timeZone: "Asia/Bangkok" })
}
