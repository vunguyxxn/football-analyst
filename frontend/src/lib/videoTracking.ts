import type { TrackingRow } from "./types.ts"

export const MAX_TRACKING_BYTES = 20 * 1024 * 1024
export const MAX_TRACKING_ROWS = 200_000
export type TrackingFrame = { frame: number; time_s: number; rows: TrackingRow[] }
export type TrackingTimeline = { frames: TrackingFrame[]; frameDuration: number; rowCount: number }

function validRow(value: unknown): value is TrackingRow {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false
  const row = value as Record<string, unknown>
  return typeof row.frame === "number" && Number.isSafeInteger(row.frame) && row.frame >= 0 &&
    typeof row.track_id === "number" && Number.isSafeInteger(row.track_id) && row.track_id >= 0 &&
    typeof row.time_s === "number" && Number.isFinite(row.time_s) && row.time_s >= 0 &&
    typeof row.x_m === "number" && Number.isFinite(row.x_m) && row.x_m >= 0 && row.x_m <= 105 &&
    typeof row.y_m === "number" && Number.isFinite(row.y_m) && row.y_m >= 0 && row.y_m <= 68 &&
    typeof row.team === "string" && ["A", "B", "referee", "unknown"].includes(row.team)
}

export function parseTracking(text: string): TrackingTimeline {
  if (new TextEncoder().encode(text).length > MAX_TRACKING_BYTES) throw new Error("File tracking vượt giới hạn 20 MB. Hãy xử lý video theo đoạn ngắn hơn.")
  const content = text.replace(/^\uFEFF/, "").trim()
  if (!content) throw new Error("File tracking chưa có dữ liệu.")
  let values: unknown[]
  try {
    values = content.startsWith("[") ? JSON.parse(content) : content.split(/\r?\n/).filter(line => line.trim()).map((line, index) => {
      try { return JSON.parse(line) }
      catch { throw new Error(`Không đọc được JSON ở dòng ${index + 1}.`) }
    })
  } catch (error) {
    throw new Error(error instanceof SyntaxError ? "File JSON không hợp lệ." : (error as Error).message)
  }
  if (!Array.isArray(values) || !values.length) throw new Error("File tracking chưa có dữ liệu.")
  if (values.length > MAX_TRACKING_ROWS) throw new Error("Tracking vượt 200.000 bản ghi. Hãy chia video thành đoạn ngắn hơn.")
  const grouped = new Map<number, TrackingFrame>()
  const keys = new Set<string>()
  for (const [index, value] of values.entries()) {
    if (!validRow(value)) throw new Error(`Bản ghi ${index + 1} không hợp lệ: cần frame, time_s, track_id, team và tọa độ trong sân 105 × 68 m.`)
    const key = `${value.frame}:${value.track_id}`
    if (keys.has(key)) throw new Error(`Trùng ID ${value.track_id} tại frame ${value.frame}.`)
    keys.add(key)
    const frame = grouped.get(value.frame)
    if (frame && Math.abs(frame.time_s - value.time_s) > 1e-6) throw new Error(`Frame ${value.frame} có nhiều mốc thời gian khác nhau.`)
    if (frame) frame.rows.push(value)
    else grouped.set(value.frame, { frame: value.frame, time_s: value.time_s, rows: [value] })
  }
  const frames = [...grouped.values()].sort((a, b) => a.frame - b.frame)
  const intervals = []
  for (let i = 1; i < frames.length; i++) {
    const previous = frames[i - 1], current = frames[i]
    if (current.time_s <= previous.time_s) throw new Error("Thời gian tracking phải tăng theo frame.")
    intervals.push((current.time_s - previous.time_s) / (current.frame - previous.frame))
  }
  intervals.sort((a, b) => a - b)
  // Infer one source-frame duration, dividing by frame gap, never by row count.
  const frameDuration = Math.min(.1, intervals.length ? intervals[Math.floor(intervals.length / 2)] : 1 / 30)
  return { frames, frameDuration, rowCount: values.length }
}

export function frameAt(timeline: TrackingTimeline | null, videoTime: number, offset: number): TrackingFrame | null {
  if (!timeline || !Number.isFinite(videoTime) || !Number.isFinite(offset)) return null
  const time = videoTime - offset
  // Media clocks can round a seek to float32 (e.g. 904/30 seconds).
  // Allow microseconds of clock error, never a missing source frame.
  const epsilon = Math.min(1e-5, timeline.frameDuration / 1000)
  let low = 0, high = timeline.frames.length
  while (low < high) {
    const middle = (low + high) >>> 1
    if (timeline.frames[middle].time_s <= time + epsilon) low = middle + 1
    else high = middle
  }
  const frame = timeline.frames[low - 1]
  // Never interpolate or retain positions through tracking/guard gaps.
  return frame && time >= frame.time_s - epsilon && time < frame.time_s + timeline.frameDuration - epsilon ? frame : null
}

export function trackingRanges(timeline: TrackingTimeline): { start: number; end: number }[] {
  const ranges: { start: number; end: number }[] = []
  for (const frame of timeline.frames) {
    const previous = ranges[ranges.length - 1]
    if (previous && frame.time_s <= previous.end + 1e-6) previous.end = frame.time_s + timeline.frameDuration
    else ranges.push({ start: frame.time_s, end: frame.time_s + timeline.frameDuration })
  }
  return ranges
}

export function compatibilityError(timeline: TrackingTimeline | null, duration: number, offset: number): string | null {
  if (!Number.isFinite(offset)) return "Nhập độ lệch thời gian hợp lệ."
  if (!timeline || !Number.isFinite(duration) || duration <= 0) return null
  const start = timeline.frames[0].time_s + offset
  const end = timeline.frames[timeline.frames.length - 1].time_s + offset
  if (end < 0 || start >= duration) return "Tracking không giao với thời lượng video. Kiểm tra video và độ lệch thời gian."
  if (start < -timeline.frameDuration || end > duration + timeline.frameDuration) return "Tracking nằm ngoài thời lượng video. Kiểm tra video và độ lệch thời gian."
  return null
}

export function formatVideoTime(time: number): string {
  const seconds = Number.isFinite(time) ? Math.max(0, time) : 0
  return `${Math.floor(seconds / 60).toString().padStart(2, "0")}:${Math.floor(seconds % 60).toString().padStart(2, "0")}`
}
