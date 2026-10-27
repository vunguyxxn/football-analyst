import { useEffect, useRef, useState } from "react"

export type ImageBox = { id: number; group: "A" | "B" | "unknown"; xyxy: number[] }
type BoxFrame = { frame: number; time_s: number; boxes: ImageBox[] }
type Result = { fps: number; frames: number; width: number; height: number; chunk_frames: number; chunks: number; device: string; track_ids: number; observations: number; limitations: string[]; source_sha256?: string }
export type VideoJob = { id: string; status: "queued" | "running" | "completed" | "failed" | "cancelled"; progress: number; stage: string; result?: Result }
type Job = VideoJob

export async function fetchCompletedDemo(jobId: string, sourceHash: string, signal: AbortSignal): Promise<VideoJob> {
  const job = await jsonResponse(await fetch(`/api/video-jobs/${jobId}`, { signal })) as VideoJob
  if (job.status !== "completed" || !job.result || job.result.source_sha256 !== sourceHash) throw new Error("Kết quả clip mẫu chưa sẵn sàng hoặc không khớp video. Hãy chuẩn bị lại clip mẫu.")
  return job
}

async function jsonResponse(response: Response) {
  const body = await response.json()
  if (!response.ok) throw new Error(body.detail || `Máy chủ trả lỗi ${response.status}`)
  return body
}

export function useVideoJob(file: File | null, clock: number) {
  const [job, setJob] = useState<Job | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadPercent, setUploadPercent] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [segment, setSegment] = useState<{ index: number; frames: BoxFrame[] } | null>(null)
  const [demoBound, setDemoBound] = useState<string | null>(null)
  const xhr = useRef<XMLHttpRequest | null>(null)
  const generation = useRef(0)
  const busy = uploading || job?.status === "running" || job?.status === "queued"
  const result = job?.status === "completed" && (file || demoBound === job.id) ? job.result : undefined
  const index = result ? Math.floor(Math.floor(clock * result.fps + .0001) / result.chunk_frames) : -1

  function reset() {
    generation.current++
    xhr.current?.abort()
    setJob(null); setSegment(null); setError(null); setUploading(false)
    setDemoBound(null)
  }

  function bindDemo(job: VideoJob) {
    generation.current++
    xhr.current?.abort()
    setSegment(null); setError(null); setUploading(false); setDemoBound(job.id); setJob(job)
  }

  useEffect(() => () => { generation.current++; xhr.current?.abort() }, [])

  useEffect(() => {
    const controller = new AbortController()
    const id = generation.current
    fetch("/api/video-jobs", { signal: controller.signal }).then(jsonResponse).then((jobs: Job[]) => {
      if (id === generation.current && !controller.signal.aborted && jobs.length) setJob(jobs[0])
    }).catch(() => { /* Upload reports connection failures when requested. */ })
    return () => controller.abort()
  }, [])

  const jobId = job?.id
  const jobStatus = job?.status
  useEffect(() => {
    if (!jobId || !jobStatus || !["queued", "running"].includes(jobStatus)) return
    let active = true
    let timer: ReturnType<typeof setTimeout>
    const controller = new AbortController()
    const poll = async () => {
      try {
        const response = await fetch(`/api/video-jobs/${jobId}`, { signal: controller.signal })
        if (response.status === 404) {
          if (active) setJob(previous => previous ? { ...previous, status: "failed", stage: "Tác vụ không còn tồn tại. Hãy chọn video và phân tích lại." } : previous)
          return
        }
        const next: Job = await jsonResponse(response)
        if (active) { setJob(next); setError(null) }
      } catch (failure) {
        if (active) setError(`Không lấy được tiến độ, đang kết nối lại: ${failure instanceof Error ? failure.message : "lỗi mạng"}`)
      }
      if (active) timer = setTimeout(poll, 1500)
    }
    timer = setTimeout(poll, 500)
    return () => { active = false; clearTimeout(timer); controller.abort() }
  }, [jobId, jobStatus])

  useEffect(() => {
    if (!result || !jobId || index < 0 || index >= result.chunks) return
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout>
    const load = () => {
      fetch(`/api/video-jobs/${jobId}/chunks/${index}`, { signal: controller.signal }).then(jsonResponse).then(body => {
        if (!controller.signal.aborted) { setSegment({ index, frames: body.frames }); setError(null) }
      }).catch(failure => {
        if (!controller.signal.aborted) {
          setError(`Không tải được khung theo dõi, đang thử lại: ${failure.message}`)
          timer = setTimeout(load, 2000)
        }
      })
    }
    load()
    return () => { clearTimeout(timer); controller.abort() }
  }, [jobId, result, index])

  async function start() {
    if (!file || busy) return
    if (file.size > 500 * 1024 * 1024) { setError("Chọn video tối đa 500 MB."); return }
    const extension = file.name.split(".").pop()?.toLowerCase()
    if (!extension || !["mp4", "webm", "mov", "mkv"].includes(extension)) { setError("Chọn MP4, WebM, MOV hoặc MKV."); return }
    const id = ++generation.current
    setError(null); setJob(null); setSegment(null); setUploading(true); setUploadPercent(0)
    const request = new XMLHttpRequest()
    xhr.current = request
    request.open("POST", `/api/video-jobs?extension=${extension}`)
    request.setRequestHeader("Content-Type", "application/octet-stream")
    request.upload.onprogress = event => { if (id === generation.current && event.lengthComputable) setUploadPercent(Math.round(event.loaded / event.total * 100)) }
    request.onload = () => {
      if (id !== generation.current) return
      setUploading(false)
      try {
        const body = JSON.parse(request.responseText)
        if (request.status !== 202) throw new Error(body.detail || "Không nhận được video.")
        setJob(body)
      } catch (failure) { setError(failure instanceof Error ? failure.message : "Phản hồi máy chủ không hợp lệ.") }
    }
    request.onerror = () => { if (id === generation.current) { setUploading(false); setError("Mất kết nối khi gửi video. Hãy kiểm tra máy chủ rồi thử lại.") } }
    request.onabort = () => { if (id === generation.current) { setUploading(false); setError("Đã dừng gửi video.") } }
    request.send(file)
  }

  async function cancel() {
    if (uploading) { xhr.current?.abort(); return }
    if (!job) return
    try {
      await jsonResponse(await fetch(`/api/video-jobs/${job.id}/cancel`, { method: "POST" }))
      setJob(previous => previous ? { ...previous, stage: "Đang dừng xử lý…" } : previous)
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Không hủy được tác vụ.") }
  }

  const frameId = result ? Math.floor(clock * result.fps + .0001) : -1
  const frame = segment?.index === index ? segment.frames[frameId - index * (result?.chunk_frames || 1)] : undefined
  return { job, busy, uploading, uploadPercent, error, start, cancel, result, frame, reset, bindDemo }
}
