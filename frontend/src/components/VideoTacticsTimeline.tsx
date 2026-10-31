import { Button } from "@/components/ui/button"
import { formatVideoTime } from "@/lib/videoTracking"

type Metrics = { width_m: number; depth_m: number; nearest_m: number; center_x_m: number }
type Sample = { support: { seconds: number; frame_coverage: number }; metrics: Metrics; evidence_time_s: number }
type Comparison = { group: string; from_segment: number; to_segment: number; from_interval: number[]; to_interval: number[]; status: string; reason: string; cohort_ids: number[]; before: Sample | null; after: Sample | null; deltas: (Metrics & { forward_m: number | null }) | null; observations: { metric: string; text: string; coach_check: string }[] }
export type TacticsTimeline = { groups: { group: string; entries: { segment: number; start_s: number; end_s: number; status: string; seconds: number }[]; comparisons: Comparison[] }[]; limits: string }
const n = (value: number) => value.toLocaleString("vi-VN", { maximumFractionDigits: 1 })
const interval = (value: number[]) => `${formatVideoTime(value[0])}–${formatVideoTime(value[1])}`
const metrics: [keyof Metrics, string][] = [["width_m", "Bề ngang cụm"], ["depth_m", "Chiều dọc cụm"], ["nearest_m", "Người cùng nhóm gần nhất"], ["center_x_m", "Tâm cụm dọc x"]]

export default function VideoTacticsTimeline({ timeline, group, selected, onSelect, onSeek }: { timeline: TacticsTimeline; group: string; selected: number; onSelect: (segment: number) => void; onSeek: (time: number) => void }) {
  const data = timeline.groups.find(item => item.group === group)
  if (!data) return null
  const valid = data.comparisons.filter(item => item.status === "observed_cohort_comparison")
  const skipped = data.comparisons.filter(item => item.status !== "observed_cohort_comparison")
  return <div className="tactics-temporal" aria-label={`Diễn biến không gian nhóm ${group}`}>
    <h4>Diễn biến theo thời gian · nhóm {group}</h4>
    <p>So cùng các ID ở hai đoạn kề nhau. Camera thấy thêm hoặc mất người không tự được coi là đội đổi chiến thuật.</p>
    <div className="tactics-window-strip">{data.entries.map((entry, index) => <div key={entry.segment}>
      {index > 0 && entry.start_s - data.entries[index - 1].end_s > .2 && <small className="tactics-gap">{formatVideoTime(data.entries[index - 1].end_s)}–{formatVideoTime(entry.start_s)}: chưa có cửa sổ hiệu chỉnh</small>}
      <button aria-pressed={entry.segment === selected} className={entry.status === "observed_cluster" ? "supported" : "unsupported"} onClick={() => onSelect(entry.segment)}><strong>{formatVideoTime(entry.start_s)}–{formatVideoTime(entry.end_s)}</strong><span>{entry.status === "observed_cluster" ? "Đủ dữ liệu đoạn" : "Chưa đủ dữ liệu đoạn"}</span><small>{n(entry.seconds)} giây đủ người</small></button>
    </div>)}</div>
    {!valid.length && <p>Chưa có hai đoạn kề nhau với cùng nhóm ID đủ hỗ trợ để so sánh.</p>}
    {valid.map(item => {
      const a = item.before!, b = item.after!, deltas = item.deltas!
      return <article key={`${item.from_segment}:${item.to_segment}`} className="tactics-comparison">
        <h4>{interval(item.from_interval)} → {interval(item.to_interval)}</h4>
        <p><strong>Cùng {item.cohort_ids.length} ID quan sát</strong> · {item.cohort_ids.join(", ")}. Chỉ so các thời điểm cả nhóm cùng hiện: {n(a.support.seconds)} giây và {n(b.support.seconds)} giây.</p>
        <div className="tactics-comparison-table"><table><caption>Số đo của cùng cụm ID, đơn vị mét</caption><thead><tr><th>Chỉ số</th><th>Đoạn trước</th><th>Đoạn sau</th><th>Thay đổi</th></tr></thead><tbody>{metrics.map(([key, label]) => <tr key={key}><th>{label}</th><td>{n(a.metrics[key])}</td><td>{n(b.metrics[key])}</td><td>{deltas[key] > 0 ? "+" : ""}{n(deltas[key])}</td></tr>)}</tbody></table></div>
        {item.observations.length ? item.observations.map(observation => <div key={observation.metric}><p><strong>{observation.text}</strong></p><p>HLV đối chiếu: {observation.coach_check}</p></div>) : <p>Các thay đổi chưa vượt ngưỡng mô tả của bộ quy tắc; chưa đủ để khẳng định chiến thuật ổn định hoặc tối ưu.</p>}
        <p>{item.reason} Các số của cụm này có thể khác chỉ số toàn nhóm áo bên dưới.</p>
        <div className="tactics-evidence-buttons"><Button variant="outline" onClick={() => onSeek(a.evidence_time_s)}>Xem đoạn trước · {formatVideoTime(a.evidence_time_s)}</Button><Button variant="outline" onClick={() => onSeek(b.evidence_time_s)}>Xem đoạn sau · {formatVideoTime(b.evidence_time_s)}</Button></div>
      </article>
    })}
    {skipped.length > 0 && <details><summary>Vì sao các đoạn khác chưa được so sánh?</summary>{skipped.map(item => <p key={`${item.from_segment}:${item.to_segment}`}><strong>{interval(item.from_interval)} → {interval(item.to_interval)}:</strong> {item.reason}</p>)}</details>}
    <p>{timeline.limits}</p>
  </div>
}
