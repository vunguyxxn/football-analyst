import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { formatVideoTime } from "@/lib/videoTracking"

type Group = "A" | "B" | "unknown"
type Summary = {
  duration_s: number; frames: number; fps: number; width: number; height: number
  average_people: number; maximum_people: number; track_ids: number; short_track_ids: number
  frames_with_people: number; observations: number; unknown_fraction: number | null
  groups: { group: Group; average_people: number; observations: number }[]
  timeline: { second: number; average_people: number; maximum_people: number; frames: number }[]
  tracks: { id: number; group: Group; observed_s: number; first_s: number; last_s: number; missing_s: number }[]
  tracks_shown: number
}
const labels = { A: "Nhóm áo A", B: "Nhóm áo B", unknown: "Chưa rõ" }
const number = (value: number, digits = 1) => value.toLocaleString("vi-VN", { maximumFractionDigits: digits })

export default function VideoTrackingReport({ jobId, onSeek, hasPitchEstimate = false }: { jobId: string; onSeek: (seconds: number) => void; hasPitchEstimate?: boolean }) {
  const [payload, setPayload] = useState<{ id: string; summary: Summary } | null>(null)
  const [failure, setFailure] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  const [showTracks, setShowTracks] = useState(false)
  const summary = payload?.id === jobId ? payload.summary : null
  useEffect(() => {
    const controller = new AbortController()
    fetch(`/api/video-jobs/${jobId}/summary`, { signal: controller.signal }).then(async response => {
      const body = await response.json()
      if (!response.ok) throw new Error(body.detail || "Không tải được báo cáo.")
      if (!controller.signal.aborted) { setPayload({ id: jobId, summary: body }); setFailure(null) }
    }).catch(error => { if (!controller.signal.aborted) setFailure(error.message) })
    return () => controller.abort()
  }, [jobId, attempt])

  return <section className="tracking-report card-surface" aria-label="Kết quả phân tích clip">
    <div className="tracking-report-heading"><div><span className="eyebrow">KẾT QUẢ TỪ VIDEO VỪA XỬ LÝ</span><h3>Kết quả phân tích clip</h3></div><span>Tracking & màu áo</span></div>
    {failure ? <div role="alert">{failure} <Button variant="outline" onClick={() => setAttempt(value => value + 1)}>Thử lại báo cáo</Button></div> : !summary ? <p role="status">Đang tổng hợp kết quả clip…</p> : <>
      <div className="tracking-report-metrics">
        <div><span>Thời lượng đã xử lý</span><strong>{number(summary.duration_s)} <small>giây</small></strong><p>{number(summary.frames, 0)} frame · {number(summary.fps)} FPS</p></div>
        <div><span>Đối tượng trung bình / frame</span><strong>{number(summary.average_people)}</strong><p>Cao nhất {summary.maximum_people} đối tượng cùng lúc</p></div>
        <div><span>Frame có phát hiện người</span><strong>{number(summary.frames_with_people / summary.frames * 100)}<small>%</small></strong><p>{number(summary.frames_with_people, 0)} / {number(summary.frames, 0)} frame</p></div>
        <div><span>Chưa phân rõ màu áo</span><strong>{summary.unknown_fraction === null ? "—" : `${number(summary.unknown_fraction * 100)}%`}</strong><p>Tính trên các lượt xuất hiện, không phải accuracy</p></div>
      </div>
      <h4>Phân bố nhóm màu áo</h4>
      <div className="tracking-report-groups">{summary.groups.map(group => <div key={group.group}><span>{labels[group.group]}</span><strong>{number(group.average_people)}</strong><p>đối tượng trung bình / frame</p></div>)}</div>
      <p>Một người xuất hiện ở nhiều frame được tính nhiều lượt. Nhóm áo chưa xác nhận đội, thủ môn hoặc trọng tài; có thể gồm người ngoài sân. Đây không phải tỷ lệ kiểm soát bóng.</p>
      <h4>Số đối tượng quan sát theo thời gian</h4>
      <p>Bấm một cột để xem lại giây tương ứng. Cột cao hơn = nhiều đối tượng được phát hiện hơn, không biểu thị cường độ vận động.</p>
      <div className="tracking-report-chart" aria-label="Biểu đồ số đối tượng theo giây">{summary.timeline.map(point => <button key={point.second} title={`${point.second}s · trung bình ${number(point.average_people)} đối tượng`} aria-label={`Xem giây ${point.second}: trung bình ${number(point.average_people)} đối tượng`} onClick={() => onSeek(point.second)} style={{ height: `${Math.max(3, point.average_people / Math.max(1, summary.maximum_people) * 100)}%` }} />)}</div>
      <div className="tracking-report-chart-labels"><span>0 giây</span><span>{number(summary.duration_s)} giây</span></div>
      <div className="tracking-report-diagnostic"><strong>Độ liên tục cần rà soát</strong><p>Tracker đã cấp {number(summary.track_ids, 0)} ID; {number(summary.short_track_ids, 0)} ID được quan sát dưới 1 giây. ID có thể đổi khi mất dấu hoặc chuyển cảnh. Các con số này không phải số cầu thủ hay số lần đổi ID đã được xác minh.</p></div>
      <Button variant="outline" onClick={() => setShowTracks(value => !value)}>{showTracks ? "Thu gọn danh sách ID" : "Xem các ID được theo dõi lâu nhất"}</Button>
      {showTracks && <div className="tracking-report-table"><p>{summary.tracks_shown} / {summary.track_ids} ID, xếp theo thời gian có quan sát. Thời gian có quan sát = số frame có ID / FPS; bỏ khoảng mất dấu, không phải phút thi đấu.</p><table><thead><tr><th>ID</th><th>Nhóm áo chủ yếu</th><th>Có quan sát</th><th>Đầu – cuối</th><th>Mất dấu ở giữa</th><th>Xem lại</th></tr></thead><tbody>{summary.tracks.map(track => <tr key={track.id}><td>{track.id}</td><td>{labels[track.group]}</td><td>{number(track.observed_s)} s</td><td>{formatVideoTime(track.first_s)} – {formatVideoTime(track.last_s)}</td><td>{number(track.missing_s)} s</td><td><button onClick={() => onSeek(track.first_s)}>Tới ID {track.id}</button></td></tr>)}</tbody></table></div>}
      <div className="tracking-report-diagnostic"><strong>Giới hạn phân tích</strong><p>{hasPitchEstimate ? "Ước lượng tọa độ sân và vận động được trình bày riêng ở trên, chỉ thuộc đoạn hiệu chỉnh và chưa kiểm chứng sai số thực địa. " : "Tọa độ sân, heatmap, quãng đường và tốc độ cần hiệu chỉnh sân. "}Ứng viên chuyền bóng vẫn cần kiểm chứng; cú sút, xG và gợi ý chiến thuật chưa được suy ra đáng tin cậy từ clip này. Báo cáo trên các trang StatsBomb/Metrica là nguồn riêng.</p></div>
    </>}
  </section>
}
