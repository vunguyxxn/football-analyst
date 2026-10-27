import { useEffect, useState } from "react"
import Pitch from "@/components/Pitch"
import { Button } from "@/components/ui/button"
import { formatVideoTime } from "@/lib/videoTracking"

type Player = { segment: number; id: number; group: string; distance_m: number; motion_s: number; mean_speed_kmh: number | null; maximum_speed_kmh: number | null; heatmap_seconds: number[][] }
type Report = { status: string; calibrated_intervals: { start_s: number; end_s: number }[]; groups: { group: string; heatmap_seconds: number[][] }[]; players: Player[]; segments: { segment: number; start_s: number; end_s: number }[]; limits: string[] }
const number = (value: number | null) => value === null ? "—" : value.toLocaleString("vi-VN", { maximumFractionDigits: 1 })

function Heatmap({ cells, label }: { cells: number[][]; label: string }) {
  const peak = Math.max(0, ...cells.flat())
  return <div className="estimate-heatmap" role="img" aria-label={label}><Pitch>{cells.flatMap((row, y) => row.map((value, x) => value > 0 ? <rect key={`${x}:${y}`} x={x * 5} y={68 - (y + 1) * 68 / 14} width="5" height={68 / 14} fill="#fb923c" opacity={.15 + .7 * value / Math.max(.001, peak)}><title>{number(value)} giây quan sát cộng dồn</title></rect> : null))}</Pitch></div>
}

export default function VideoPitchEstimate({ jobId, onSeek }: { jobId: string; onSeek: (seconds: number) => void }) {
  const [payload, setPayload] = useState<{ id: string; report: Report } | null>(null)
  const [failure, setFailure] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  const [group, setGroup] = useState("A")
  const [selection, setSelection] = useState("")
  useEffect(() => {
    const controller = new AbortController()
    fetch(`/api/video-jobs/${jobId}/pitch-estimate`, { signal: controller.signal }).then(async response => {
      const body = await response.json()
      if (!response.ok || body.status !== "provisional_estimate") throw new Error(body.detail || "Chưa có ước lượng sân cho clip này.")
      if (!controller.signal.aborted) { setPayload({ id: jobId, report: body }); setFailure(null) }
    }).catch(error => { if (!controller.signal.aborted) setFailure(error.message) })
    return () => controller.abort()
  }, [jobId, attempt])
  const report = payload?.id === jobId ? payload.report : null
  const eligible = report?.players.filter(player => player.motion_s >= 1) || []
  const player = eligible.find(item => `${item.segment}:${item.id}` === selection) || eligible[0]
  const team = report?.groups.find(item => item.group === group)
  return <section className="tracking-report card-surface" aria-label="Heatmap và vận động ước lượng">
    <span className="eyebrow">ƯỚC LƯỢNG TỪ VIDEO · CHƯA KIỂM CHỨNG SAI SỐ THỰC ĐỊA</span><h3>Heatmap và vận động</h3>
    {failure ? <p role="alert">{failure} <Button variant="outline" onClick={() => setAttempt(value => value + 1)}>Thử lại ước lượng</Button></p> : !report ? <p role="status">Đang đọc ước lượng chuyển động…</p> : <>
      <div className="tracking-report-diagnostic"><strong>Chỉ tính đoạn {report.calibrated_intervals.map(interval => `${formatVideoTime(interval.start_s)}–${formatVideoTime(interval.end_s)}`).join(", ")}</strong><p>Mốc sân do agent chọn tay, sân giả định 105×68 m. Đây là số đo ước lượng, chưa có đánh giá sai số độc lập; không phải số liệu toàn clip/toàn trận.</p><Button variant="outline" onClick={() => onSeek((report.calibrated_intervals[0]?.start_s || 0) + .2)}>Xem đoạn có tọa độ</Button></div>
      <div className="pitch-estimate-layout"><div><h4>Vùng hoạt động của nhóm áo</h4><label>Chọn nhóm áo <select aria-label="Nhóm áo của heatmap" value={group} onChange={event => setGroup(event.target.value)}><option value="A">Nhóm áo A</option><option value="B">Nhóm áo B</option><option value="unknown">Chưa rõ</option></select></label>{team && <Heatmap cells={team.heatmap_seconds} label={`Heatmap ước lượng nhóm ${group}`} />}<p>Ô sáng hơn = nhiều thời gian vị trí được quan sát hơn. Nhiều người cùng xuất hiện được cộng dồn; không phải kiểm soát bóng. Mỗi bản đồ chuẩn hóa theo đỉnh riêng.</p></div>
      <div><h4>Vận động theo ID trong đoạn quan sát</h4>{player ? <><label>Chọn quỹ đạo <select aria-label="ID của chỉ số vận động" value={`${player.segment}:${player.id}`} onChange={event => setSelection(event.target.value)}>{eligible.map(item => { const scope = report.segments.find(segment => segment.segment === item.segment); return <option key={`${item.segment}:${item.id}`} value={`${item.segment}:${item.id}`}>ID {item.id} · {item.group} · {scope ? `${formatVideoTime(scope.start_s)}–${formatVideoTime(scope.end_s)}` : `đoạn ${item.segment}`}</option> })}</select></label><div className="tracking-report-metrics estimate-metrics"><div><span>Quãng đường hợp lệ</span><strong>{number(player.distance_m)} <small>m</small></strong></div><div><span>Tốc độ trung bình</span><strong>{number(player.mean_speed_kmh)} <small>km/h</small></strong></div><div><span>Tốc độ cao nhất</span><strong>{number(player.maximum_speed_kmh)} <small>km/h</small></strong></div><div><span>Thời gian chuyển động được tính</span><strong>{number(player.motion_s)} <small>giây</small></strong></div></div><Heatmap cells={player.heatmap_seconds} label={`Heatmap ước lượng ID ${player.id}`} /></> : <p>Chưa đủ quỹ đạo liên tục để tính vận động.</p>}<p>ID là mã theo dõi, không phải số áo hay danh tính cầu thủ. Không nối qua khoảng mất dấu hoặc đổi mốc sân; loại các khoảng vượt 40 km/h, không ép tốc độ về ngưỡng.</p></div></div>
    </>}
  </section>
}
