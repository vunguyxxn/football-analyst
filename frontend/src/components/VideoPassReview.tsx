import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { formatVideoTime } from "@/lib/videoTracking"

type Event = { start_s: number; end_s: number; from_id: number; to_id: number; group: string }
export default function VideoPassReview({ jobId, onSeek, hasPitchEstimate = false }: { jobId: string; onSeek: (seconds: number) => void; hasPitchEstimate?: boolean }) {
  const [payload, setPayload] = useState<{ id: string; events: Event[] } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    fetch(`/api/video-jobs/${jobId}/ball-events`, { signal: controller.signal }).then(async response => {
      const body = await response.json()
      if (!response.ok) throw new Error(body.detail || "Không tải được tình huống.")
      if (!controller.signal.aborted) { setPayload({ id: jobId, events: body.possible_passes }); setError(null) }
    }).catch(failure => { if (!controller.signal.aborted) setError(failure.message) })
    return () => controller.abort()
  }, [jobId, attempt])
  const events = payload?.id === jobId ? payload.events : null
  return <section className="tracking-report card-surface" aria-label="Tình huống chuyền bóng thử nghiệm">
    <span className="eyebrow">NHẬN DIỆN SỰ KIỆN TỪ VIDEO · THỬ NGHIỆM</span>
    <h3>Các tình huống có thể là đường chuyền</h3>
    <p>Ứng viên từ chuỗi bám bóng và liên kết gần chân cầu thủ. Cần rà soát tình huống; chưa dùng làm tổng số chuyền bóng, tỷ lệ chính xác hoặc đánh giá chiến thuật.</p>
    {error ? <div role="alert">{error} <Button variant="outline" onClick={() => setAttempt(value => value + 1)}>Thử lại tình huống</Button></div> : !events ? <p role="status">Đang đọc tình huống…</p> : events.length ? <div className="pass-review-list">{events.map((event, index) => <article key={`${event.start_s}:${event.from_id}`}><div><strong>Tình huống {index + 1} · {formatVideoTime(event.start_s)}–{formatVideoTime(event.end_s)}</strong><p>Nhóm áo {event.group} · ID {event.from_id} → ID {event.to_id}</p><small>Ứng viên chưa xác nhận · ID là mã tracking, không phải số áo</small></div><Button variant="outline" onClick={() => onSeek(Math.max(0, event.start_s - .5))}>Xem tình huống {index + 1}</Button></article>)}</div> : <p>Chưa có ứng viên đạt điều kiện. Điều này không có nghĩa clip không có đường chuyền.</p>}
    <p>Chưa có bộ nhận diện cú sút đã kiểm chứng; không ghi số cú sút bằng 0. {hasPitchEstimate ? "Heatmap và vận động ở phần trên chỉ thuộc đoạn hiệu chỉnh, chưa có kiểm chứng sai số độc lập." : "Heatmap, quãng đường và tốc độ của clip này còn cần hiệu chỉnh sân đạt yêu cầu."}</p>
  </section>
}
