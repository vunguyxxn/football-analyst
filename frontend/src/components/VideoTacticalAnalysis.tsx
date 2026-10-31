import { useEffect, useState } from "react"
import Pitch from "@/components/Pitch"
import { Button } from "@/components/ui/button"
import { formatVideoTime } from "@/lib/videoTracking"
import VideoTacticsTimeline, { type TacticsTimeline } from "@/components/VideoTacticsTimeline"

type Position = { id?: number; slot?: number; x_m: number; y_m: number }
type Candidate = { shape: string; rmse_m: number; agreement: number; reference_time_s: number; observed_people: number; missing_outfield_slots: number; attack_direction_hypothesis: number; observed_players: Position[]; unseen_slots: Position[] }
type Advice = { id: string; title: string; observation: string; condition: string; actions: string[]; tradeoff: string; formation_option: string; source: { title: string; url: string } }
type Window = { segment: number; group: string; start_s: number; end_s: number; status: string; review?: { team_label: string; attack_direction: number | null; note: string | null; review_times_s: number[] } | null; support: { seconds: number; frame_coverage: number }; metrics: null | { median_width_m: number; median_depth_m: number; median_nearest_neighbor_m: number; median_people: number; lane_shares: number[] }; heatmap_seconds: number[][] | null; snapshot: null | { time_s: number; players: Position[] }; formation: { status: string; shape: string | null; reason: string; candidates: Candidate[] }; recommendations: Advice[] }
type Report = { status: string; message?: string; timeline?: TacticsTimeline; context_review?: { team_labels: Record<string, string>; removed_team_observations: number; audit: { sampled_people: number; outfield_people: number; correct_outfield_group: number; referee_in_team_groups: number; referee_samples: number } } | null; windows: Window[]; formation_options: { shape: string; players: Position[] }[] }
const n = (value: number) => value.toLocaleString("vi-VN", { maximumFractionDigits: 1 })
const color = (group: string) => group === "A" ? "#c084fc" : "#22d3ee"

function People({ people, ghost = false, group }: { people: Position[]; ghost?: boolean; group: string }) {
  return <>{people.map(person => <g key={person.id ?? person.slot}>
    <circle cx={person.x_m} cy={68 - person.y_m} r="1.6" fill={ghost ? "#111923" : color(group)} stroke={ghost ? "#cbd5e1" : "white"} strokeWidth=".35" strokeDasharray={ghost ? "1 .8" : undefined}><title>{ghost ? `Ô mẫu ${person.slot}: giả định, không quan sát được` : `ID ${person.id} thực sự quan sát`}</title></circle>
    <text x={person.x_m} y={68 - person.y_m - 2.5} textAnchor="middle" fill={ghost ? "#cbd5e1" : "white"} fontSize="2.4">{ghost ? "?" : person.id}</text>
  </g>)}</>
}

export default function VideoTacticalAnalysis({ jobId, onSeek }: { jobId: string; onSeek: (time: number) => void }) {
  const [payload, setPayload] = useState<{ id: string; report: Report } | null>(null)
  const [failure, setFailure] = useState<{ id: string; message: string } | null>(null)
  const [attempt, setAttempt] = useState(0)
  const [selection, setSelection] = useState("")
  const [shape, setShape] = useState("")
  const [option, setOption] = useState("")
  useEffect(() => {
    const controller = new AbortController()
    fetch(`/api/video-jobs/${jobId}/tactics`, { signal: controller.signal }).then(async response => {
      const body = await response.json()
      if (!response.ok) throw new Error(body.detail || "Không đọc được phân tích chiến thuật.")
      if (!Array.isArray(body.windows)) throw new Error("Dữ liệu chiến thuật chưa hợp lệ.")
      if (!controller.signal.aborted) { setPayload({ id: jobId, report: body }); setFailure(null); setSelection(""); setShape(""); setOption("") }
    }).catch(error => { if (!controller.signal.aborted) setFailure({ id: jobId, message: error.message }) })
    return () => controller.abort()
  }, [jobId, attempt])
  const report = payload?.id === jobId ? payload.report : null
  const error = failure?.id === jobId ? failure.message : null
  const window = report?.windows.find(item => `${item.segment}:${item.group}` === selection) || report?.windows[0]
  const candidate = window?.formation.candidates.find(item => item.shape === shape) || window?.formation.candidates[0]
  const board = report?.formation_options?.find(item => item.shape === option)
  const peak = Math.max(.001, ...(window?.heatmap_seconds?.flat() || []))
  return <section className="tracking-report card-surface video-tactics" aria-label="Phân tích chiến thuật từ video">
    <span className="eyebrow">HEATMAP · HÌNH THÁI ĐỘI · GỢI Ý HLV</span><h3>Đọc chiến thuật từ phần sân quan sát được</h3>
    <p>Không cần camera thấy đủ 11 người. Chỉ số tính từ người thực sự nhìn thấy; sơ đồ là các giả thuyết hình học, chưa phải chiến thuật đã xác nhận.</p>
    {error ? <p role="alert">{error} <Button variant="outline" onClick={() => { setFailure(null); setAttempt(value => value + 1) }}>Thử lại chiến thuật</Button></p>
      : !report ? <p role="status">Đang phân tích không gian và so các giả thuyết đội hình…</p>
      : report.status === "not_available" ? <p className="tracking-report-diagnostic">{report.message}</p>
      : window && <>
        {report.context_review && <div className="tracking-report-diagnostic"><strong>Đã rà nội bộ: A = {report.context_review.team_labels.A.toLowerCase()} · B = {report.context_review.team_labels.B.toLowerCase()}</strong><p>Mẫu gốc có {report.context_review.audit.referee_in_team_groups}/{report.context_review.audit.referee_samples} lần trọng tài lẫn vào nhóm đội. Phân tích chiến thuật đã loại thêm {report.context_review.removed_team_observations.toLocaleString("vi-VN")} lượt vị trí thuộc quỹ đạo trọng tài/thủ môn đã rà. Khung tracking và bảng vận động tổng hợp vẫn giữ nhóm màu gốc.</p><p>Đối chiếu {report.context_review.audit.correct_outfield_group}/{report.context_review.audit.outfield_people} mẫu cầu thủ sân đúng nhóm trong tổng {report.context_review.audit.sampled_people} mẫu người. Đây là rà bằng ảnh bởi agent, chưa phải đánh giá độc lập hoặc độ chính xác toàn clip.</p></div>}
        <label className="tactics-selector">Nhóm áo và đoạn phân tích <select aria-label="Đoạn phân tích chiến thuật" value={`${window.segment}:${window.group}`} onChange={event => { setSelection(event.target.value); setShape(""); setOption("") }}>{report.windows.map(item => <option key={`${item.segment}:${item.group}`} value={`${item.segment}:${item.group}`}>Nhóm {item.group} · {formatVideoTime(item.start_s)}–{formatVideoTime(item.end_s)}</option>)}</select></label>
        {report.timeline && <VideoTacticsTimeline timeline={report.timeline} group={window.group} selected={window.segment} onSelect={segment => { setSelection(`${segment}:${window.group}`); setShape(""); setOption("") }} onSeek={onSeek} />}
        <p>Đủ dữ liệu trong {n(window.support.seconds)} giây ({n(window.support.frame_coverage * 100)}% đoạn). Tọa độ sân 105 × 68 m được hiệu chỉnh tay, còn là ước lượng.</p>
        {window.review && <div className="tracking-report-diagnostic"><strong>{window.review.team_label}{window.review.attack_direction ? ` · hướng tấn công suy luận ${window.review.attack_direction > 0 ? "sang phải →" : "sang trái ←"}` : " · chưa có hướng tấn công được rà cho đoạn này"}</strong>{window.review.note && <p>{window.review.note}</p>}<p>Hướng và vai trò do agent rà từ video, chưa xác nhận bằng thông tin trận đấu chính thức. Chỉ dùng hướng này khi so mẫu trong đoạn đã rà.</p><div className="tactics-evidence-buttons">{window.review.review_times_s.map(time => <Button key={time} variant="outline" onClick={() => onSeek(time)}>Ảnh rà · {formatVideoTime(time)}</Button>)}</div></div>}
        {!window.metrics ? <p>Chưa đủ ít nhất 4 người cùng nhóm trong 5 giây và 50% đoạn để đưa ra số đo hoặc gợi ý.</p> : <>
          <div className="tracking-report-metrics estimate-metrics">
            <div><span>Số người thấy cùng lúc (trung vị)</span><strong>{n(window.metrics.median_people)}</strong></div>
            <div><span>Bề ngang cụm</span><strong>{n(window.metrics.median_width_m)} <small>m</small></strong></div>
            <div><span>Chiều dọc cụm</span><strong>{n(window.metrics.median_depth_m)} <small>m</small></strong></div>
            <div><span>Cự ly người cùng nhóm gần nhất</span><strong>{n(window.metrics.median_nearest_neighbor_m)} <small>m</small></strong></div>
          </div>
          <div className="pitch-estimate-layout tactics-maps">
            <div><h4>Heatmap hoạt động · nhóm {window.group}</h4><div className="estimate-heatmap" role="img" aria-label={`Heatmap chiến thuật nhóm ${window.group}`}><Pitch>{window.heatmap_seconds?.flatMap((row, y) => row.map((value, x) => value > 0 ? <rect key={`${x}:${y}`} x={x * 5} y={68 - (y + 1) * 68 / 14} width="5" height={68 / 14} fill="#fb923c" opacity={.12 + .75 * value / peak}><title>{n(value)} giây vị trí cộng dồn</title></rect> : null))}</Pitch></div><p>Vùng sáng = nhiều thời gian vị trí được nhìn thấy. Vùng tối có thể nằm ngoài camera, không có nghĩa bị bỏ trống. Chuẩn hóa màu riêng từng bản đồ.</p><p>Phân bố lượt vị trí theo chiều ngang sân: y thấp {n(window.metrics.lane_shares[0] * 100)}% · trung lộ {n(window.metrics.lane_shares[1] * 100)}% · y cao {n(window.metrics.lane_shares[2] * 100)}%. Đây không phải tỷ lệ kiểm soát bóng.</p></div>
            <div><h4>Hình thái quan sát cùng thời điểm</h4><div className="estimate-heatmap" role="img" aria-label="Vị trí thực tế cùng thời điểm"><Pitch><People people={window.snapshot?.players || []} group={window.group} /></Pitch></div><p>Mỗi chấm là một ID nhìn thấy trong cùng khung hình; không ghép vị trí từ nhiều thời điểm thành 11 người.</p><Button variant="outline" onClick={() => onSeek(window.snapshot!.time_s)}>Xem đoạn làm căn cứ · {formatVideoTime(window.snapshot!.time_s)}</Button></div>
          </div>
          <div className="tactics-formation"><h4>Các khả năng về sơ đồ đội hình</h4><p>{window.formation.reason} Mức tin cậy thấp; {window.review?.attack_direction ? "đã lọc vai trò theo rà nội bộ và so mẫu theo hướng suy luận, chưa xác nhận sơ đồ độc lập." : "vai trò thủ môn và hướng tấn công chưa được xác nhận."}</p>
            {window.formation.candidates.length > 0 && <>
              <div className="tactics-candidates">{window.formation.candidates.map(item => <button className={candidate?.shape === item.shape ? "selected" : ""} key={item.shape} onClick={() => setShape(item.shape)} aria-pressed={candidate?.shape === item.shape}><strong>{item.shape}</strong><span>Sai lệch mẫu {n(item.rmse_m)} m</span><span>Đứng đầu {n(item.agreement * 100)}% mẫu thời điểm</span></button>)}</div>
              <p>Sai lệch thấp hơn = khớp hình học tốt hơn trong các mẫu đã thử. Tỷ lệ đứng đầu đo sự nhất quán trên 3–4 thời điểm, không phải xác suất sơ đồ đúng. Sai lệch trên 6 m chưa đạt ngưỡng thử nghiệm.</p>
              {candidate && <div className="tactics-hypothesis"><div className="estimate-heatmap" role="img" aria-label={`Giả thuyết sơ đồ ${candidate.shape}`}><Pitch><People people={candidate.unseen_slots} ghost group={window.group} /><People people={candidate.observed_players} group={window.group} /></Pitch></div><div><strong>Giả thuyết {candidate.shape} · {formatVideoTime(candidate.reference_time_s)}</strong><p>{candidate.observed_people} người quan sát, {candidate.missing_outfield_slots} ô mẫu chưa ghép với người quan sát. Chấm màu có ID = quan sát; vòng nét đứt “?” = vị trí giả định, không phải cầu thủ phát hiện được.</p><p>Mẫu giả sử nhóm quan sát là cầu thủ sân, tấn công theo x {candidate.attack_direction_hypothesis > 0 ? "tăng →" : "giảm ←"}. Không suy ra danh tính, thủ môn hoặc vị trí thật ngoài camera. Các ô giả định không vào heatmap/quãng đường.</p><Button variant="outline" onClick={() => onSeek(candidate.reference_time_s)}>Đối chiếu video của giả thuyết</Button></div></div>}
            </>}
          </div>
          <h4>Nhận xét và phương án chiến thuật để HLV cân nhắc</h4><p>Các quy tắc không gian chọn vấn đề cần xem lại. Chưa có nhận diện pha có bóng/không bóng hoặc mô hình chứng minh chiến thuật tối ưu.</p>
          <div className="tactics-advice">{window.recommendations.map(advice => <article key={advice.id}><h4>{advice.title}</h4><p><strong>Căn cứ:</strong> {advice.observation}</p><p><strong>Điều kiện áp dụng:</strong> {advice.condition}</p><ul>{advice.actions.map(action => <li key={action}>{action}</li>)}</ul><p><strong>Đánh đổi:</strong> {advice.tradeoff}</p><div className="tactics-advice-footer"><a href={advice.source.url} target="_blank" rel="noreferrer">Nguyên tắc tham khảo FIFA</a><Button variant="outline" onClick={() => setOption(option === advice.formation_option ? "" : advice.formation_option)}>Minh họa phương án {advice.formation_option}</Button></div></article>)}</div>
          {board && <div className="tactics-hypothesis"><div className="estimate-heatmap"><Pitch>{board.players.map(person => <circle key={person.slot} cx={person.x_m} cy={68 - person.y_m} r="1.7" fill="#fbbf24" />)}</Pitch></div><p>Phương án tập luyện {board.shape}, tấn công sang phải. Đây là bố trí minh họa để HLV thử theo điều kiện ở trên; chưa phải sơ đồ nhận diện hoặc phương án đã được chứng minh phù hợp nhất.</p></div>}
        </>}
      </>}
  </section>
}
