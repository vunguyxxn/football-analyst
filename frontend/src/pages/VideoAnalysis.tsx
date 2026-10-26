import { useEffect, useMemo, useRef, useState } from "react"
import { AlertCircle, Clapperboard, FileJson, FolderOpen, LoaderCircle, LocateFixed, Play, Upload } from "lucide-react"
import Pitch from "@/components/Pitch"
import { Button } from "@/components/ui/button"
import { toSvg } from "@/lib/pitchCoordinates"
import { compatibilityError, formatVideoTime, frameAt, MAX_TRACKING_BYTES, parseTracking, trackingRanges } from "@/lib/videoTracking"
import type { TrackingTimeline } from "@/lib/videoTracking"

type VideoSource = { url: string; name: string; initialTime: number; id: number }
const TEAMS = { A: { label: "Đội A", color: "#a855f7" }, B: { label: "Đội B", color: "#22d3ee" }, referee: { label: "Trọng tài", color: "#facc15" }, unknown: { label: "Chưa rõ", color: "#94a3b8" } }

export default function VideoAnalysis() {
  const video = useRef<HTMLVideoElement>(null)
  const requestId = useRef(0)
  const pending = useRef<AbortController | null>(null)
  const [source, setSource] = useState<VideoSource | null>(null)
  const [timeline, setTimeline] = useState<TrackingTimeline | null>(null)
  const [trackingName, setTrackingName] = useState("")
  const [offsetInput, setOffsetInput] = useState("0")
  const [clock, setClock] = useState(0)
  const [duration, setDuration] = useState(0)
  const [seeking, setSeeking] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mediaError, setMediaError] = useState<string | null>(null)
  const [showIds, setShowIds] = useState(true)
  const offset = offsetInput.trim() ? Number(offsetInput) : NaN
  const mismatch = compatibilityError(timeline, duration, offset)
  const sample = !source || !duration || seeking || mismatch || mediaError ? null : frameAt(timeline, clock, offset)
  const ranges = useMemo(() => timeline ? trackingRanges(timeline) : [], [timeline])

  useEffect(() => () => { requestId.current++; pending.current?.abort() }, [])
  useEffect(() => () => { if (source?.url.startsWith("blob:")) URL.revokeObjectURL(source.url) }, [source])

  useEffect(() => {
    const element = video.current
    if (!element || !source) return
    let active = true, handle = 0
    if (typeof element.requestVideoFrameCallback === "function") {
      const tick: VideoFrameRequestCallback = (_now, metadata) => {
        if (!active) return
        setClock(metadata.mediaTime)
        handle = element.requestVideoFrameCallback(tick)
      }
      handle = element.requestVideoFrameCallback(tick)
      return () => { active = false; element.cancelVideoFrameCallback(handle) }
    }
    const tick = () => {
      if (!active) return
      if (!element.paused && !element.seeking) setClock(element.currentTime)
      handle = requestAnimationFrame(tick)
    }
    handle = requestAnimationFrame(tick)
    return () => { active = false; cancelAnimationFrame(handle) }
  }, [source])

  function cancelPending() {
    pending.current?.abort()
    requestId.current++
    setLoading(false)
    return requestId.current
  }

  function seekTo(time: number) {
    const element = video.current
    if (!element || !duration || !Number.isFinite(time)) return
    const target = Math.max(0, Math.min(duration, time))
    if (Math.abs(element.currentTime - target) < 1e-7) { setClock(target); return }
    setSeeking(true)
    element.currentTime = target
  }

  async function openDemo() {
    const id = cancelPending()
    const controller = new AbortController()
    pending.current = controller
    video.current?.pause()
    setLoading(true); setError(null)
    try {
      const [manifestResponse, trackingResponse] = await Promise.all([
        fetch("/video-demo/manifest.json", { signal: controller.signal }),
        fetch("/video-demo/tracking.jsonl", { signal: controller.signal }),
      ])
      if (!manifestResponse.ok || !trackingResponse.ok || !manifestResponse.headers.get("content-type")?.includes("application/json")) throw new Error("Clip mẫu chưa có sẵn. Bạn có thể chọn video và tracking cục bộ bên dưới.")
      const manifest = await manifestResponse.json()
      if (manifest.version !== 1 || typeof manifest.offset_seconds !== "number" || !Number.isFinite(manifest.offset_seconds)) throw new Error("Thông tin clip mẫu không hợp lệ.")
      const data = parseTracking(await trackingResponse.text())
      if (id !== requestId.current) return
      setTimeline(data); setTrackingName("Tracking clip mẫu")
      setOffsetInput(String(manifest.offset_seconds)); setClock(0); setDuration(0); setSeeking(false); setMediaError(null)
      setSource({ url: "/video-demo/video.mp4", name: "Clip mẫu · sân 11 người", initialTime: data.frames[0].time_s + manifest.offset_seconds, id })
    } catch (failure) {
      if (id === requestId.current && !controller.signal.aborted) setError(failure instanceof Error ? failure.message : "Không mở được clip mẫu.")
    } finally { if (id === requestId.current) setLoading(false) }
  }

  function openVideo(file?: File) {
    if (!file) return
    const id = cancelPending()
    video.current?.pause()
    setTimeline(null); setTrackingName(""); setDuration(0); setClock(0); setOffsetInput("0"); setSeeking(false); setError(null); setMediaError(null)
    setSource({ url: URL.createObjectURL(file), name: file.name, initialTime: 0, id })
  }

  async function openTracking(file?: File) {
    if (!file) return
    const id = cancelPending()
    video.current?.pause()
    setTimeline(null); setTrackingName(""); setError(null)
    if (file.size > MAX_TRACKING_BYTES) { setError("File tracking vượt giới hạn 20 MB. Hãy chọn một đoạn ngắn hơn."); return }
    setLoading(true)
    try {
      const data = parseTracking(await file.text())
      if (id !== requestId.current) return
      setTimeline(data); setTrackingName(file.name)
      if (!compatibilityError(data, duration, offset) && duration) seekTo(data.frames[0].time_s + offset)
    } catch (failure) { if (id === requestId.current) setError(failure instanceof Error ? failure.message : "Không đọc được tracking.") }
    finally { if (id === requestId.current) setLoading(false) }
  }

  return <div className="video-page">
    <section className="video-intro">
      <div><span className="eyebrow">VIDEO & CHUYỂN ĐỘNG</span><h2>Theo sát từng chuyển động.</h2><p>Xem video và vị trí trên sân trong cùng một nhịp.</p></div>
      <Button className="demo-button" disabled={loading} onClick={openDemo} size="lg">{loading ? <LoaderCircle className="animate-spin" /> : <Play />}Mở clip mẫu</Button>
    </section>

    <section aria-label="Mở dữ liệu video" className="video-files card-surface">
      <label className="video-file-input"><span className="file-icon"><Clapperboard size={19} /></span><span><strong>Video trận đấu</strong><small>{source?.name || "Chọn MP4, WebM hoặc video tương thích"}</small></span><Upload aria-hidden="true" size={17} /><input accept="video/*" aria-label="Chọn video" onChange={event => { openVideo(event.target.files?.[0]); event.target.value = "" }} type="file" /></label>
      <label className="video-file-input"><span className="file-icon"><FileJson size={19} /></span><span><strong>Dữ liệu vị trí</strong><small>{loading ? "Đang đọc dữ liệu…" : trackingName || "Chọn file tracking JSONL hoặc JSON"}</small></span><Upload aria-hidden="true" size={17} /><input accept=".jsonl,.json,application/json" aria-label="Chọn tracking" onChange={event => { void openTracking(event.target.files?.[0]); event.target.value = "" }} type="file" /></label>
    </section>
    {(error || mediaError || mismatch) && <div className="error-notice" role="alert"><AlertCircle size={18} /><span>{error || mediaError || mismatch}</span></div>}

    <div className="video-analysis-grid">
      <section aria-label="Trình phát video" className="video-player-card card-surface">
        <div className="video-panel-heading"><h3><Clapperboard size={17} /> Video trận đấu</h3><span className="video-local-tag">CỤC BỘ</span></div>
        <div className="video-screen">
          {source ? <video controls key={source.id} onError={() => { setMediaError("Không phát được video. Hãy chọn video MP4 mã hóa H.264 hoặc WebM."); setDuration(0) }} onLoadedMetadata={event => {
            const element = event.currentTarget
            if (!Number.isFinite(element.duration) || element.duration <= 0) { setMediaError("Không đọc được thời lượng video."); return }
            setDuration(element.duration)
            if (source.initialTime > 0 && source.initialTime < element.duration) { setSeeking(true); element.currentTime = source.initialTime }
          }} onSeeked={event => { setClock(event.currentTarget.currentTime); setSeeking(false) }} onSeeking={() => setSeeking(true)} onTimeUpdate={event => {
            if (typeof event.currentTarget.requestVideoFrameCallback !== "function" || event.currentTarget.paused) setClock(event.currentTarget.currentTime)
          }} playsInline preload="metadata" ref={video} src={source.url} /> : <div className="video-empty"><span className="video-empty-icon"><Clapperboard size={36} strokeWidth={1.3} /></span><h3>Đưa trận đấu vào góc nhìn mới</h3><p>Mở clip mẫu để xem ngay, hoặc chọn video<br />và dữ liệu vị trí đã xử lý của bạn.</p><span><FolderOpen size={14} /> Tệp được mở trên máy của bạn</span></div>}
        </div>
        <div className="video-timeline">
          <div className="video-time-row"><span>{formatVideoTime(clock)} <span>/ {formatVideoTime(duration)}</span></span><span>{sample ? `Frame ${sample.frame}` : "—"}</span></div>
          <div className="video-seek-wrap">
            <div aria-hidden="true" className="tracking-coverage">{duration > 0 && !mismatch && ranges.map(range => <i key={range.start} style={{ left: `${Math.max(0, (range.start + offset) / duration * 100)}%`, width: `${Math.max(0, Math.min(duration, range.end + offset) - Math.max(0, range.start + offset)) / duration * 100}%` }} />)}</div>
            <input aria-label="Tua video" disabled={!duration} max={duration || 1} min="0" onChange={event => seekTo(Number(event.target.value))} step="any" type="range" value={Math.min(clock, duration || 0)} />
          </div>
          <div className="video-time-row video-coverage-caption"><span><i /> Đoạn có tọa độ</span><button disabled={!timeline || !duration || !!mismatch} onClick={() => timeline && seekTo(timeline.frames[0].time_s + offset)}><LocateFixed size={13} />Tới đoạn có tọa độ</button></div>
        </div>
      </section>

      <section aria-label="Vị trí trên sân" className="mini-pitch-card card-surface">
        <div className="video-panel-heading"><h3><LocateFixed size={17} /> Góc nhìn trên sân</h3><span className={`position-status${sample ? " has-positions" : ""}`}><i />{sample ? "Đang đồng bộ" : "Chưa có tọa độ"}</span></div>
        <div className="mini-pitch-wrap"><Pitch className="video-mini-pitch">{sample?.rows.map(row => {
          const point = toSvg(row.x_m, row.y_m), team = TEAMS[row.team]
          return <g key={row.track_id}><circle cx={point.x} cy={point.y} fill={team.color} r="1.35" stroke="#f8fafc" strokeWidth=".25"><title>{`${team.label} · ID ${row.track_id} · (${row.x_m.toFixed(1)}, ${row.y_m.toFixed(1)}) m`}</title></circle>{showIds && <text className="tracking-id" x={point.x} y={point.y - 2.1}>{row.track_id}</text>}</g>
        })}</Pitch></div>
        <div className="mini-pitch-summary"><strong>{sample?.rows.length ?? 0}<small>đối tượng tại thời điểm này</small></strong><label><input checked={showIds} onChange={event => setShowIds(event.target.checked)} type="checkbox" />Hiện ID</label></div>
        <div className="video-team-legend">{Object.entries(TEAMS).map(([key, team]) => <span key={key}><i style={{ background: team.color }} />{team.label}</span>)}</div>
        <div aria-live="polite" className="mini-pitch-message">{!source ? "Mở video và dữ liệu vị trí để bắt đầu." : !timeline ? "Chọn file tracking tương ứng với video." : mismatch ? "Kiểm tra căn chỉnh thời gian trước khi xem vị trí." : seeking ? "Đang chuyển tới thời điểm mới…" : !sample ? "Thời điểm này chưa có tọa độ hợp lệ. Sân mini được để trống." : "ID là mã theo dõi, không phải số áo. Tọa độ giữ nguyên hướng sân của video."}</div>
      </section>
    </div>

    <section className="video-notes card-surface">
      <div><strong>Chỉ hiển thị dữ liệu có sẵn</strong><p>Đoạn mất hiệu chỉnh hoặc thiếu tracking sẽ để trống. Tọa độ hiện dùng để minh họa, chưa dùng đo quãng đường hay tốc độ thực địa.</p></div>
      <details><summary>Căn chỉnh thời gian</summary><label>Mốc 0 của tracking trong video (giây)<input aria-label="Độ lệch thời gian" onChange={event => { video.current?.pause(); setOffsetInput(event.target.value) }} step="0.01" type="number" value={offsetInput} /></label><p>Cùng một đoạn video: nhập 0. Nếu tracking được tạo từ đoạn cắt bắt đầu ở giây 10 của video đang mở: nhập 10.</p></details>
    </section>
  </div>
}
