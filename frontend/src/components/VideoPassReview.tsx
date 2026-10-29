import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { formatVideoTime } from "@/lib/videoTracking"

type Event = { start_s: number; end_s: number; from_id: number; to_id: number; group: string }
const reviewTime = (seconds: number) => `${formatVideoTime(seconds)},${Math.floor(seconds * 10 + 1e-6) % 10}`
type Audit = { point_diagnostic: { tp: number; visible_samples: number; uncertain_skipped: number; tolerance_px: number }; event_diagnostic: { pass: { tp: number; reference_count: number; fn: number; missed_reference_ids: string[] } }; reviewed_events: { id: string; kind: string; start_s: number; end_s: number; group: string }[] }
export default function VideoPassReview({ jobId, onSeek, hasPitchEstimate = false }: { jobId: string; onSeek: (seconds: number) => void; hasPitchEstimate?: boolean }) {
  const [payload, setPayload] = useState<{ id: string; events: Event[]; validation: Audit | null } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    fetch(`/api/video-jobs/${jobId}/ball-events`, { signal: controller.signal }).then(async response => {
      const body = await response.json()
      if (!response.ok) throw new Error(body.detail || "Không tải được tình huống.")
      if (!controller.signal.aborted) { setPayload({ id: jobId, events: body.possible_passes, validation: body.validation || null }); setError(null) }
    }).catch(failure => { if (!controller.signal.aborted) setError(failure.message) })
    return () => controller.abort()
  }, [jobId, attempt])
  const events = payload?.id === jobId ? payload.events : null
  const audit = payload?.id === jobId ? payload.validation : null
  return <section className="tracking-report card-surface" aria-label="Tình huống chuyền bóng thử nghiệm">
    <span className="eyebrow">NHẬN DIỆN SỰ KIỆN TỪ VIDEO · THỬ NGHIỆM</span>
    <h3>Các tình huống có thể là đường chuyền</h3>
    <p>Ứng viên từ chuỗi bám bóng và liên kết gần chân cầu thủ. Cần rà soát tình huống; chưa dùng làm tổng số chuyền bóng, tỷ lệ chính xác hoặc đánh giá chiến thuật.</p>
    {error ? <div role="alert">{error} <Button variant="outline" onClick={() => setAttempt(value => value + 1)}>Thử lại tình huống</Button></div> : !events ? <p role="status">Đang đọc tình huống…</p> : events.length ? <div className="pass-review-list">{events.map((event, index) => <article key={`${event.start_s}:${event.from_id}`}><div><strong>Tình huống {index + 1} · {reviewTime(event.start_s)}–{reviewTime(event.end_s)}</strong><p>Nhóm áo {event.group} · ID {event.from_id} → ID {event.to_id}</p><small>Ứng viên chưa xác nhận · ID là mã tracking, không phải số áo</small></div><Button variant="outline" onClick={() => onSeek(Math.max(0, event.start_s - .5))}>Xem tình huống {index + 1}</Button></article>)}</div> : <p>Chưa có ứng viên đạt điều kiện. Điều này không có nghĩa clip không có đường chuyền.</p>}
    {audit && <div className="tracking-report-diagnostic" aria-label="Đối chiếu bóng và chuyền trên mẫu phát triển"><strong>Đối chiếu với video gốc · chưa kiểm định độc lập</strong><p>Trong các đoạn được rà, AI nhận ra {audit.event_diagnostic.pass.tp}/{audit.event_diagnostic.pass.reference_count} đường chuyền do agent đánh dấu, còn bỏ sót {audit.event_diagnostic.pass.fn}. Chưa đủ tin cậy để đếm tổng chuyền tự động.</p><p>Vị trí bóng khớp {audit.point_diagnostic.tp}/{audit.point_diagnostic.visible_samples} mẫu nhìn rõ trong dung sai {audit.point_diagnostic.tolerance_px} pixel; bỏ qua {audit.point_diagnostic.uncertain_skipped} mẫu không chắc. Đây là mẫu phát triển nhỏ, không đại diện toàn clip hoặc video khác.</p><div className="pass-review-list">{audit.reviewed_events.filter(event => audit.event_diagnostic.pass.missed_reference_ids.includes(event.id)).map((event, index) => <article key={event.id}><div><strong>Đường chuyền bị bỏ sót · {reviewTime(event.start_s)}–{reviewTime(event.end_s)}</strong><p>Nhóm áo {event.group} · mốc do agent rà trên ảnh gốc</p></div><Button variant="outline" onClick={() => onSeek(Math.max(0, event.start_s - .5))}>Xem đường chuyền bỏ sót {index + 1}</Button></article>)}</div><p>Các đoạn rà chưa có mẫu cú sút dương tính; chưa đánh giá được khả năng nhận diện sút. Chuyền về phía sân nhà không được coi là sút chỉ vì bóng đi về phía khung thành trong ảnh.</p></div>}
    <p>Chưa có bộ nhận diện cú sút đã kiểm chứng; không ghi số cú sút bằng 0. {hasPitchEstimate ? "Heatmap và vận động ở phần trên chỉ thuộc đoạn hiệu chỉnh, chưa có kiểm chứng sai số độc lập." : "Heatmap, quãng đường và tốc độ của clip này còn cần hiệu chỉnh sân đạt yêu cầu."}</p>
  </section>
}
