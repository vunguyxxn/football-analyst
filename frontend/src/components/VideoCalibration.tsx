import { useState, type RefObject } from "react"
import Pitch from "@/components/Pitch"
import { Button } from "@/components/ui/button"
import { formatVideoTime } from "@/lib/videoTracking"
import type { ManualPitch, VideoJob } from "@/lib/useVideoJob"

const LANDMARKS = [
  { label: "Giữa sân × biên xa", xy: [52.5, 68] }, { label: "Giữa sân × biên gần", xy: [52.5, 0] },
  { label: "Giữa sân × vòng tròn phía xa", xy: [52.5, 43.15] }, { label: "Giữa sân × vòng tròn phía gần", xy: [52.5, 24.85] },
  { label: "Cung phạt đền phải phía xa", xy: [88.5, 41.3125] }, { label: "Cung phạt đền phải phía gần", xy: [88.5, 26.6875] },
  { label: "Cung phạt đền trái phía xa", xy: [16.5, 41.3125] }, { label: "Cung phạt đền trái phía gần", xy: [16.5, 26.6875] },
  { label: "Góc vùng cấm phải phía xa", xy: [88.5, 54.16] }, { label: "Góc vùng cấm phải phía gần", xy: [88.5, 13.84] },
  { label: "Góc vùng cấm trái phía xa", xy: [16.5, 54.16] }, { label: "Góc vùng cấm trái phía gần", xy: [16.5, 13.84] },
  { label: "Góc vùng 5,5m phải phía xa", xy: [99.5, 43.16] }, { label: "Góc vùng 5,5m phải phía gần", xy: [99.5, 24.84] },
  { label: "Góc vùng 5,5m trái phía xa", xy: [5.5, 43.16] }, { label: "Góc vùng 5,5m trái phía gần", xy: [5.5, 24.84] },
  { label: "Góc sân phải phía xa", xy: [105, 68] }, { label: "Góc sân phải phía gần", xy: [105, 0] },
  { label: "Góc sân trái phía xa", xy: [0, 68] }, { label: "Góc sân trái phía gần", xy: [0, 0] },
]
const PRESETS = { right: [0, 1, 8, 16, 2, 3], left: [0, 1, 10, 18, 2, 3], rightBox: [8, 9, 12, 13, 4, 5], leftBox: [10, 11, 14, 15, 6, 7] }

export default function VideoCalibration({ video, job, busy, onApply, ranges, onSeek }: {
  video: RefObject<HTMLVideoElement | null>; job: VideoJob; busy: boolean; onApply: (payload?: ManualPitch) => Promise<void>;
  ranges: { start: number; end: number }[]; onSeek: (time: number) => void
}) {
  const [snapshot, setSnapshot] = useState<{ url: string; frame: number; width: number; height: number } | null>(null)
  const [targets, setTargets] = useState(PRESETS.right)
  const [points, setPoints] = useState<(number[] | null)[]>(Array(6).fill(null))
  const [active, setActive] = useState(0)
  const [zoom, setZoom] = useState(1)
  const [failure, setFailure] = useState<string | null>(null)
  const result = job.result
  let coveredEnd = 0
  let gap: number | null = null
  for (const range of ranges) {
    if (range.start - coveredEnd >= 1) { gap = coveredEnd + .5; break }
    coveredEnd = Math.max(coveredEnd, range.end)
  }
  if (gap === null && result && result.frames / result.fps - coveredEnd >= 1) gap = coveredEnd + .5

  function capture() {
    const element = video.current
    if (!element || !result || !element.videoWidth) return
    element.pause()
    if (element.videoWidth !== result.width || element.videoHeight !== result.height) {
      setFailure("Kích thước video không khớp tác vụ. Hãy mở lại đúng video."); return
    }
    try {
      const canvas = document.createElement("canvas")
      canvas.width = element.videoWidth; canvas.height = element.videoHeight
      canvas.getContext("2d")!.drawImage(element, 0, 0)
      setSnapshot({ url: canvas.toDataURL("image/jpeg", .9), frame: Math.min(result.frames - 1, Math.floor(element.currentTime * result.fps + .0001)), width: canvas.width, height: canvas.height })
      setPoints(Array(6).fill(null)); setTargets(PRESETS.right); setActive(0); setZoom(1); setFailure(null)
    } catch { setFailure("Không chụp được khung hình. Hãy chờ video tải xong rồi thử lại.") }
  }

  async function submit() {
    if (!snapshot || !result?.source_sha256 || points.some(point => !point)) return
    try {
      setFailure(null)
      await onApply({ frame: snapshot.frame, source_sha256: result.source_sha256, image_points: points as number[][], pitch_points: targets.map(index => LANDMARKS[index].xy) })
      setSnapshot(null)
    } catch (error) { setFailure(error instanceof Error ? error.message : "Không áp dụng được mốc sân.") }
  }

  return <section className="tracking-report card-surface video-calibration" aria-label="Hiệu chỉnh sân trong ứng dụng">
    <span className="eyebrow">HOÀN THIỆN PHÂN TÍCH VIDEO</span><h3>Hiệu chỉnh sân và tính lại kết quả</h3>
    <p>AI tự tìm mốc sân trước. Nếu còn đoạn trống, tua video tới ảnh rõ vạch rồi chọn mốc tại đây. Máy sẽ bù chuyển động camera và dừng tọa độ khi mất dấu.</p>
    <p>Sân giả định 105×68m. Chọn 4 giao điểm để hiệu chỉnh và 2 mốc khác để đối chiếu; không cần nhập tọa độ hay chạy lệnh.</p>
    <div className="calibration-actions"><Button disabled={busy} onClick={capture}>Chụp khung hình hiện tại</Button>{gap !== null && <Button disabled={busy} variant="outline" onClick={() => { video.current?.pause(); setSnapshot(null); onSeek(gap!); video.current?.scrollIntoView({ behavior: "smooth", block: "center" }) }}>Tới đoạn chưa có tọa độ</Button>}<Button disabled={busy} variant="outline" onClick={() => { setFailure(null); void onApply().catch(error => setFailure(error.message)) }}>Thử lại tự động</Button></div>
    {failure && <p role="alert" className="calibration-error">{failure}</p>}
    {snapshot && <>
      <p><strong>Khung đã giữ tại {formatVideoTime(snapshot.frame / (result?.fps || 1))}.</strong> Chọn số mốc rồi bấm đúng giao vạch trên ảnh lớn; sơ đồ bên cạnh chỉ vị trí tương ứng trên sân.</p>
      <label>Mẫu mốc phù hợp với ảnh <select aria-label="Mẫu mốc sân" disabled={busy} onChange={event => { setTargets(PRESETS[event.target.value as keyof typeof PRESETS]); setPoints(Array(6).fill(null)); setActive(0) }} defaultValue="right"><option value="right">Giữa sân và vùng cấm phải</option><option value="left">Giữa sân và vùng cấm trái</option><option value="rightBox">Vùng cấm và vùng 5,5m phải</option><option value="leftBox">Vùng cấm và vùng 5,5m trái</option></select></label>
      <div className="calibration-actions"><span>Phóng to để chọn chính xác, cuộn ảnh để di chuyển:</span>{[1, 2, 3].map(scale => <Button key={scale} variant="outline" aria-pressed={zoom === scale} onClick={() => setZoom(scale)}>{scale}×</Button>)}</div>
      <div className="calibration-grid">
        <div className="calibration-viewport"><div className="calibration-image" style={{ width: `${zoom * 100}%` }} onClick={event => {
          if (busy) return
          const rect = event.currentTarget.getBoundingClientRect()
          const point = [(event.clientX - rect.left) / rect.width * snapshot.width, (event.clientY - rect.top) / rect.height * snapshot.height]
          setPoints(previous => previous.map((value, i) => i === active ? point : value))
          setActive(Math.min(5, active + 1))
        }} role="img" aria-label={`Ảnh chọn mốc sân, đang chọn mốc ${active + 1}`}>
          <img src={snapshot.url} alt="Khung video để chọn giao điểm vạch sân" draggable={false} />
          <svg viewBox={`0 0 ${snapshot.width} ${snapshot.height}`} aria-hidden="true">{points.map((point, i) => point && <g key={i}><circle cx={point[0]} cy={point[1]} r="10" fill={i < 4 ? "#fbbf24" : "#e879f9"} stroke="black" strokeWidth="2" /><text x={point[0] + 14} y={point[1] - 12} fill="white" stroke="black" strokeWidth="1" paintOrder="stroke" fontSize="28">{i+1}</text></g>)}</svg>
        </div></div>
        <div><Pitch>{targets.map((index, i) => <g key={i}><circle cx={LANDMARKS[index].xy[0]} cy={68 - LANDMARKS[index].xy[1]} r="2" fill={i === active ? "#fbbf24" : "#cbd5e1"} /><text x={LANDMARKS[index].xy[0] + (LANDMARKS[index].xy[0] > 100 ? -5 : 2.5)} y={LANDMARKS[index].xy[1] > 63 ? 68 - LANDMARKS[index].xy[1] + 5 : 68 - LANDMARKS[index].xy[1] - 2} fontSize="4" fill="white">{i+1}</text></g>)}</Pitch>
          {targets.map((index, i) => <div className={`calibration-point${i === active ? " selected" : ""}`} key={i}>
            <button disabled={busy} onClick={() => setActive(i)} aria-pressed={i === active}>{i+1} {points[i] ? "✓" : "○"}</button>
            <label>{i < 4 ? "Hiệu chỉnh" : "Đối chiếu"}<select aria-label={`Loại mốc ${i+1}`} disabled={busy} value={index} onChange={event => { setTargets(previous => previous.map((v, j) => i === j ? Number(event.target.value) : v)); setPoints(previous => previous.map((v,j) => i === j ? null : v)); setActive(i) }}>{LANDMARKS.map((mark,j) => <option value={j} key={j}>{mark.label}</option>)}</select></label>
          </div>)}
        </div>
      </div>
      <div className="calibration-actions"><Button disabled={busy || points.some(point => !point)} onClick={() => { void submit() }}>Áp dụng mốc và phân tích tiếp</Button><Button disabled={busy} variant="outline" onClick={() => setPoints(previous => previous.map((value, i) => i === active ? null : value))}>Xóa mốc đang chọn</Button><Button disabled={busy} variant="outline" onClick={() => setSnapshot(null)}>Đóng chọn mốc</Button></div>
    </>}
  </section>
}
