import { useEffect, useMemo, useRef, useState } from "react"
import { AlertCircle, Clapperboard, FileJson, FolderOpen, LoaderCircle, LocateFixed, Play, Upload } from "lucide-react"
import Pitch from "@/components/Pitch"
import { Button } from "@/components/ui/button"
import { toSvg } from "@/lib/pitchCoordinates"
import { compatibilityError, formatVideoTime, frameAt, MAX_TRACKING_BYTES, parseTracking, trackingRanges } from "@/lib/videoTracking"
import type { TrackingTimeline } from "@/lib/videoTracking"
import { fetchCompletedDemo, useVideoJob } from "@/lib/useVideoJob"
import VideoTrackingReport from "@/components/VideoTrackingReport"
import VideoTacticalAnalysis from "@/components/VideoTacticalAnalysis"
import VideoPitchEstimate from "@/components/VideoPitchEstimate"

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
  const [sourceFile, setSourceFile] = useState<File | null>(null)
  const ai = useVideoJob(sourceFile, clock)
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
    if (ai.busy) return
    ai.reset()
    setSourceFile(null)
    const id = cancelPending()
    const controller = new AbortController()
    pending.current = controller
    video.current?.pause()
    setLoading(true); setError(null)
    try {
      const manifestResponse = await fetch("/video-demo/manifest.json", { signal: controller.signal, cache: "no-store" })
      if (!manifestResponse.ok || !manifestResponse.headers.get("content-type")?.includes("application/json")) throw new Error("Clip mẫu chưa có sẵn. Bạn có thể chọn video và tracking cục bộ bên dưới.")
      const manifest = await manifestResponse.json()
      if (manifest.version === 2 && manifest.kind === "processed_video_job") {
        if (typeof manifest.job_id !== "string" || !/^[a-f0-9]{32}$/.test(manifest.job_id) || typeof manifest.video_sha256 !== "string" || !/^[a-f0-9]{64}$/.test(manifest.video_sha256) || typeof manifest.name !== "string") throw new Error("Thông tin clip mẫu không hợp lệ.")
        const job = await fetchCompletedDemo(manifest.job_id, manifest.video_sha256, controller.signal)
        let pitch: TrackingTimeline | null = null
        if (job.result?.pitch_estimate_available) {
          try {
            const response = await fetch(`/api/video-jobs/${manifest.job_id}/pitch-tracking`, { signal: controller.signal })
            if (!response.ok) throw new Error("Tọa độ sân mẫu chưa đọc được.")
            pitch = parseTracking(await response.text())
          } catch (failure) { if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : "Chưa đọc được tọa độ.") }
        }
        if (id !== requestId.current) return
        setTimeline(pitch); setTrackingName(pitch ? "Ước lượng sân clip mẫu" : ""); setOffsetInput("0"); setClock(0); setDuration(0); setSeeking(false); setMediaError(null)
        ai.bindDemo(job)
        setSource({ url: `/video-demo/${manifest.job_id}.mp4`, name: manifest.name, initialTime: pitch?.frames[0].time_s || 0, id })
        return
      }
      if (manifest.version !== 1 || typeof manifest.offset_seconds !== "number" || !Number.isFinite(manifest.offset_seconds)) throw new Error("Thông tin clip mẫu không hợp lệ.")
      const trackingResponse = await fetch("/video-demo/tracking.jsonl", { signal: controller.signal })
      if (!trackingResponse.ok) throw new Error("Chưa có tọa độ cho clip mẫu.")
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
    if (!file || ai.busy) return
    ai.reset()
    const id = cancelPending()
    video.current?.pause()
    setTimeline(null); setTrackingName(""); setDuration(0); setClock(0); setOffsetInput("0"); setSeeking(false); setError(null); setMediaError(null)
    setSource({ url: URL.createObjectURL(file), name: file.name, initialTime: 0, id })
    setSourceFile(file)
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
      <div><span className="eyebrow">VIDEO & CHUYỂN ĐỘNG</span><h2>Phân tích video của bạn.</h2><p>Chọn video, bấm Phân tích video và chờ AI xử lý trên máy chủ cục bộ.</p></div>
      <Button className="demo-button" disabled={loading || ai.busy} onClick={openDemo} size="lg">{loading ? <LoaderCircle className="animate-spin" /> : <Play />}Mở clip mẫu</Button>
    </section>

    <section className="video-job card-surface" aria-label="Phân tích AI">
      <div><strong>Theo dõi người trong sân và ước lượng nhóm màu áo</strong><p>Clip tối đa 10 phút / 500 MB. Video được gửi tới máy chủ đang chạy trên máy này. Lọc người ngoài sân theo vạch trắng; sân mini và chỉ số mét cần hiệu chỉnh sân riêng.</p></div>
      <Button disabled={!sourceFile || !duration || !!mediaError || ai.busy || loading} onClick={() => { video.current?.pause(); void ai.start() }}>{ai.busy ? <LoaderCircle className="animate-spin" /> : <Play />}Phân tích video</Button>
      {ai.busy && <Button variant="outline" onClick={() => { void ai.cancel() }}>Hủy xử lý</Button>}
      {(ai.uploading || ai.job) && <div className="video-job-status" role="status"><span>{ai.uploading ? `Đang gửi video: ${ai.uploadPercent}%` : ai.job?.status === "completed" ? "Đã xử lý video" : ai.job?.stage}</span><progress aria-label="Tiến độ phân tích" max="100" value={ai.uploading ? ai.uploadPercent : ai.job?.progress || 0} /><span>{!ai.uploading && ai.job ? `${Math.round(ai.job.progress)}%${ai.result ? ` · ${ai.result.device === "cpu" ? "CPU" : "GPU"}` : ""}` : ""}</span></div>}
      {ai.error && <p role="alert">{ai.error}</p>}
      {ai.result && <div><strong>{ai.result.pitch_estimate_available ? "Đã có kết quả — xem heatmap, các giả thuyết sơ đồ và gợi ý chiến thuật bên dưới." : "Đã có tracking người trong sân. Clip này cần hiệu chỉnh sân để phân tích không gian theo mét."}</strong>{ai.result.limitations.filter(note => !ai.result?.pitch_estimate_available || !note.startsWith("Chưa hiệu chỉnh")).map(note => <p key={note}>{note}</p>)}{ai.result.pitch_estimate_available && <p>Vị trí, heatmap và vận động chỉ là ước lượng cho đoạn đã hiệu chỉnh; chưa kiểm chứng sai số thực địa. Xem phạm vi bên dưới.</p>}</div>}
    </section>

    <section aria-label="Mở dữ liệu video" className="video-files card-surface">
      <label className="video-file-input"><span className="file-icon"><Clapperboard size={19} /></span><span><strong>Video trận đấu</strong><small>{source?.name || "Chọn MP4, WebM hoặc video tương thích"}</small></span><Upload aria-hidden="true" size={17} /><input disabled={ai.busy} accept="video/*" aria-label="Chọn video" onChange={event => { openVideo(event.target.files?.[0]); event.target.value = "" }} type="file" /></label>
      <label className="video-file-input"><span className="file-icon"><FileJson size={19} /></span><span><strong>Dữ liệu vị trí</strong><small>{loading ? "Đang đọc dữ liệu…" : trackingName || "Chọn file tracking JSONL hoặc JSON"}</small></span><Upload aria-hidden="true" size={17} /><input accept=".jsonl,.json,application/json" aria-label="Chọn tracking" onChange={event => { void openTracking(event.target.files?.[0]); event.target.value = "" }} type="file" /></label>
    </section>
    {(error || mediaError || mismatch) && <div className="error-notice" role="alert"><AlertCircle size={18} /><span>{error || mediaError || mismatch}</span></div>}

    <div className={`video-analysis-grid${ai.result && !timeline ? " video-result-grid" : ""}`}>
      <section aria-label="Trình phát video" className="video-player-card card-surface">
        <div className="video-panel-heading"><h3><Clapperboard size={17} /> Video trận đấu</h3><span className="video-local-tag">CỤC BỘ</span></div>
        <div className="video-screen" style={ai.result ? { aspectRatio: `${ai.result.width} / ${ai.result.height}` } : undefined}>
          {source ? <video controls key={source.id} onError={() => { setMediaError("Không phát được video. Hãy chọn video MP4 mã hóa H.264 hoặc WebM."); setDuration(0) }} onLoadedMetadata={event => {
            const element = event.currentTarget
            if (!Number.isFinite(element.duration) || element.duration <= 0) { setMediaError("Không đọc được thời lượng video."); return }
            setDuration(element.duration)
            if (source.initialTime > 0 && source.initialTime < element.duration) { setSeeking(true); element.currentTime = source.initialTime }
          }} onSeeked={event => { setClock(event.currentTarget.currentTime); setSeeking(false) }} onSeeking={() => setSeeking(true)} onTimeUpdate={event => {
            if (typeof event.currentTarget.requestVideoFrameCallback !== "function" || event.currentTarget.paused) setClock(event.currentTarget.currentTime)
          }} playsInline preload="metadata" ref={video} src={source.url} /> : <div className="video-empty"><span className="video-empty-icon"><Clapperboard size={36} strokeWidth={1.3} /></span><h3>Đưa trận đấu vào góc nhìn mới</h3><p>Chọn video rồi bấm Phân tích video,<br />hoặc mở clip mẫu để xem ngay.</p><span><FolderOpen size={14} /> Xử lý trên máy chủ cục bộ</span></div>}
          {ai.result && !seeking && !mediaError && <svg className="video-box-overlay" viewBox={`0 0 ${ai.result.width} ${ai.result.height}`} aria-label={`Khung theo dõi: ${ai.frame?.boxes.length || 0} người`}>
            {ai.frame?.pitch_boundary && <polygon points={ai.frame.pitch_boundary.map(point => point.join(",")).join(" ")} fill="none" stroke="#ffffff" strokeWidth="3" strokeDasharray="12 8"><title>Biên sân ước lượng từ vạch trắng; chỉ theo dõi điểm chân bên trong</title></polygon>}
            {ai.frame?.boxes.map(box => { const [x1, y1, x2, y2] = box.xyxy; const color = TEAMS[box.group].color; return <g key={box.id}><rect x={x1} y={y1} width={Math.max(0, x2 - x1)} height={Math.max(0, y2 - y1)} fill="none" stroke={color} strokeWidth="3" />{showIds && <text x={x1} y={Math.max(16, y1 - 5)} fill={color} stroke="#000" strokeWidth=".7" paintOrder="stroke" fontSize="18">{box.group} · ID {box.id}</text>}</g> })}
          </svg>}
        </div>
        <div className="video-timeline">
          {ai.result && <label className="video-overlay-options"><input checked={showIds} onChange={event => setShowIds(event.target.checked)} type="checkbox" />Hiện ID trên video</label>}
          <div className="video-time-row"><span>{formatVideoTime(clock)} <span>/ {formatVideoTime(duration)}</span></span><span>{sample ? `Frame ${sample.frame}` : "—"}</span></div>
          <div className="video-seek-wrap">
            <div aria-hidden="true" className="tracking-coverage">{duration > 0 && !mismatch && ranges.map(range => <i key={range.start} style={{ left: `${Math.max(0, (range.start + offset) / duration * 100)}%`, width: `${Math.max(0, Math.min(duration, range.end + offset) - Math.max(0, range.start + offset)) / duration * 100}%` }} />)}</div>
            <input aria-label="Tua video" disabled={!duration} max={duration || 1} min="0" onChange={event => seekTo(Number(event.target.value))} step="any" type="range" value={Math.min(clock, duration || 0)} />
          </div>
          <div className="video-time-row video-coverage-caption"><span><i /> {timeline ? "Đoạn có tọa độ" : "Chưa có dữ liệu vị trí"}</span><button disabled={!timeline || !duration || !!mismatch} onClick={() => timeline && seekTo(timeline.frames[0].time_s + offset)}><LocateFixed size={13} />Tới đoạn có tọa độ</button></div>
        </div>
      </section>

      {(!ai.result || timeline) && <section aria-label="Vị trí trên sân" className="mini-pitch-card card-surface">
        <div className="video-panel-heading"><h3><LocateFixed size={17} /> Góc nhìn trên sân</h3><span className={`position-status${sample ? " has-positions" : ""}`}><i />{sample ? "Đang đồng bộ" : "Chưa có tọa độ"}</span></div>
        <div className="mini-pitch-wrap"><Pitch className="video-mini-pitch">{sample?.rows.map(row => {
          const point = toSvg(row.x_m, row.y_m), team = TEAMS[row.team]
          return <g key={row.track_id}><circle cx={point.x} cy={point.y} fill={team.color} r="1.35" stroke="#f8fafc" strokeWidth=".25"><title>{`${team.label} · ID ${row.track_id} · (${row.x_m.toFixed(1)}, ${row.y_m.toFixed(1)}) m`}</title></circle>{showIds && <text className="tracking-id" x={point.x} y={point.y - 2.1}>{row.track_id}</text>}</g>
        })}</Pitch></div>
        <div className="mini-pitch-summary"><strong>{sample?.rows.length ?? 0}<small>đối tượng tại thời điểm này</small></strong><label><input checked={showIds} onChange={event => setShowIds(event.target.checked)} type="checkbox" />Hiện ID</label></div>
        <div className="video-team-legend">{Object.entries(TEAMS).map(([key, team]) => <span key={key}><i style={{ background: team.color }} />{team.label}</span>)}</div>
        <div aria-live="polite" className="mini-pitch-message">{!source ? "Chọn video để bắt đầu." : !timeline ? ai.result ? "Đã có khung theo dõi trên video. Sân mini cần hiệu chỉnh sân cho clip này; chưa có tọa độ mét." : ai.busy ? "AI đang xử lý khung theo dõi trên video; chưa có hiệu chỉnh sân để vẽ vị trí tại đây." : "Bấm Phân tích video để chạy AI. Nếu đã có tọa độ sân được hiệu chỉnh, bạn có thể mở file tracking tương ứng." : mismatch ? "Kiểm tra căn chỉnh thời gian trước khi xem vị trí." : seeking ? "Đang chuyển tới thời điểm mới…" : !sample ? "Thời điểm này chưa có tọa độ hợp lệ. Sân mini được để trống." : "ID là mã theo dõi, không phải số áo. Tọa độ giữ nguyên hướng sân của video."}</div>
      </section>}
    </div>

    {ai.result && ai.job && <>
      <VideoTacticalAnalysis key={`tactics-${ai.job.id}`} jobId={ai.job.id} onSeek={seconds => { video.current?.pause(); seekTo(seconds); video.current?.scrollIntoView({ behavior: "smooth", block: "center" }) }} />
      {ai.result.pitch_estimate_available && <details className="tracking-diagnostics"><summary>Heatmap tổng hợp và vận động theo ID</summary><VideoPitchEstimate key={`pitch-${ai.job.id}`} jobId={ai.job.id} onSeek={seconds => { video.current?.pause(); seekTo(seconds); video.current?.scrollIntoView({ behavior: "smooth", block: "center" }) }} /></details>}
      <details className="tracking-diagnostics"><summary>Thông tin xử lý và chẩn đoán tracking</summary><VideoTrackingReport key={ai.job.id} hasPitchEstimate={ai.result.pitch_estimate_available} jobId={ai.job.id} onSeek={seconds => { video.current?.pause(); seekTo(seconds); video.current?.scrollIntoView({ behavior: "smooth", block: "center" }) }} /></details>
    </>}

    <section className="video-notes card-surface">
      <div><strong>Chỉ hiển thị dữ liệu có sẵn</strong><p>Đoạn mất hiệu chỉnh hoặc thiếu tracking sẽ để trống. Tọa độ hiện dùng để minh họa, chưa dùng đo quãng đường hay tốc độ thực địa.</p></div>
      <details><summary>Căn chỉnh thời gian</summary><label>Mốc 0 của tracking trong video (giây)<input aria-label="Độ lệch thời gian" onChange={event => { video.current?.pause(); setOffsetInput(event.target.value) }} step="0.01" type="number" value={offsetInput} /></label><p>Cùng một đoạn video: nhập 0. Nếu tracking được tạo từ đoạn cắt bắt đầu ở giây 10 của video đang mở: nhập 10.</p></details>
    </section>
  </div>
}
