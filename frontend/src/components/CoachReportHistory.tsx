import { useEffect, useState } from "react"
import type { CoachReport } from "@/lib/coachReport"
import { coachOpenedTime, coachProvenance, coachReportFingerprint, readCoachHistory, saveCoachHistory } from "@/lib/coachHistory"
import type { CoachHistoryEntry } from "@/lib/coachHistory"

export default function CoachReportHistory({ report, name, onOpen }: {
  report: CoachReport | undefined
  name: string
  onOpen: (entry: CoachHistoryEntry) => Promise<void>
}) {
  const [history, setHistory] = useState<{ entries: CoachHistoryEntry[]; notice: string }>(() => {
    try { return { entries: readCoachHistory(window.localStorage), notice: "" } }
    catch (error) { return { entries: [], notice: error instanceof Error ? error.message : "Không đọc được lịch sử trên trình duyệt." } }
  })
  const { entries, notice } = history
  const [busy, setBusy] = useState(false)
  const [snapshot, setSnapshot] = useState<{ report: CoachReport; id: string; openedAt: string } | null>(null)
  useEffect(() => {
    if (!report) return
    let active = true
    const openedAt = new Date().toISOString()
    const content = JSON.stringify(report.original)
    void coachReportFingerprint(content).then(id => {
      if (active) setSnapshot({ report, id, openedAt })
    }).catch(() => { if (active) setSnapshot(null) })
    void (async () => saveCoachHistory(window.localStorage, report, name, openedAt))().then(items => {
      if (active) setHistory({ entries: items, notice: "" })
    }).catch(error => {
      if (active) setHistory(previous => ({ ...previous, notice: error instanceof Error ? error.message : "Không lưu được lịch sử; báo cáo đang mở vẫn được giữ." }))
    })
    return () => { active = false }
  }, [report, name])
  const current = snapshot?.report === report ? snapshot : null
  const provenance = report ? coachProvenance(report) : null

  async function open(entry: CoachHistoryEntry) {
    setBusy(true)
    try { await onOpen(entry) }
    catch (error) { setHistory(previous => ({ ...previous, notice: error instanceof Error ? error.message : "Không mở được báo cáo đã lưu." })) }
    finally { setBusy(false) }
  }

  return <section className="coach-history card-surface" aria-label="Nguồn và lịch sử báo cáo">
    <h3>Nguồn và phiên bản báo cáo</h3>
    {report && <dl className="coach-provenance">
      <div><dt>Thời điểm tạo do JSON ghi</dt><dd>{provenance?.generatedAt ? coachOpenedTime(provenance.generatedAt) : "Báo cáo chưa ghi thời điểm tạo"}</dd></div>
      <div><dt>Lần mở này · giờ Việt Nam/Thái Lan (UTC+7)</dt><dd>{current ? coachOpenedTime(current.openedAt) : "Đang xác định…"}</dd></div>
      <div><dt>Phiên bản nội dung</dt><dd>{current ? <code title={current.id}>{current.id.slice(0, 16)}</code> : "Chưa xác định"}</dd></div>
    </dl>}
    {report && <details className="coach-provenance-details"><summary>Định danh nguồn và mô hình</summary>
      <p>Ngày mở không phải ngày tạo hoặc ngày cập nhật dữ liệu. Mã nội dung phân biệt các bản báo cáo đã lưu.</p>
      <p>SHA256 mô hình: <code>{report.modelHash}</code></p>
      <p>Revision dữ liệu: <code>{provenance?.sourceRevision ?? "JSON chưa ghi mã hợp lệ"}</code></p>
      <p>SHA256 sự kiện: <code>{provenance?.eventsHash ?? "JSON chưa ghi mã hợp lệ"}</code></p>
      {current && <p>SHA256 nội dung: <code>{current.id}</code></p>}
    </details>}
    <details className="coach-history-list"><summary>Báo cáo gần đây ({entries.length})</summary>
      <p>Lưu tối đa 5 bản trong giới hạn 2 MB trên trình duyệt này; bản cũ nhất nhường chỗ khi đầy. File được đọc tại máy, không gửi lên server.</p>
      {entries.length ? <ul>{entries.map(entry => <li key={entry.id}>
        <div><strong>{entry.teams.join(" — ") || `Trận ${entry.matchId}`}</strong><span>{entry.name} · Trận {entry.matchId}</span><small>Mở lần cuối {coachOpenedTime(entry.openedAt)} · bản {entry.id.slice(0, 12)}</small></div>
        <button disabled={busy} onClick={() => void open(entry)}>Mở báo cáo</button>
      </li>)}</ul> : <p>Chưa có báo cáo được lưu trong trình duyệt này.</p>}
    </details>
    {notice && <p role="status" className="coach-history-notice">Lịch sử: {notice}</p>}
  </section>
}
