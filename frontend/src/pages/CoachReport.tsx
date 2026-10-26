import { useEffect, useRef, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { AlertCircle, ArrowDownToLine, ArrowUpRight, ClipboardList, FileJson, Layers, LoaderCircle, SearchCheck } from "lucide-react"
import { Button } from "@/components/ui/button"
import { COACH_FEATURES, COACH_LABELS, coachTime, MAX_COACH_BYTES, parseCoachReport } from "@/lib/coachReport"
import type { CoachReport as Report, CoachShot } from "@/lib/coachReport"
import { formatProfileMetric as metric } from "@/lib/playerProfiles"
import "./coachReport.css"

function ShotExplanation({ shot }: { shot: CoachShot }) {
  const peak = Math.max(...COACH_FEATURES.map(key => Math.abs(shot.shap[key])), 1e-8)
  return <section aria-label="Giải thích cú sút" className="coach-explanation"><div className="coach-section-heading"><h4>Vì sao mô hình cho xG này?</h4><span>SHAP · log-odds</span></div><div className="coach-shot-identity"><div><strong>{shot.shortName}</strong><span>{coachTime(shot)} · Hiệp {shot.period} · Index #{shot.index}</span></div><strong className="shot-probability">{metric(shot.xg, 3)}<small>xG</small></strong></div><p className="coach-explanation-caption">Đóng góp so với nền mô hình: xanh làm tăng dự đoán, hồng làm giảm dự đoán. Giá trị SHAP không phải điểm phần trăm.</p><div className="coach-shap-heading"><span>Feature / giá trị</span><span>Đóng góp SHAP</span></div><div className="coach-shap-bars">{COACH_FEATURES.map(key => <div className="coach-shap-row" key={key}><div><span>{COACH_LABELS[key]}</span><small>{metric(shot.features[key], 3)}</small></div><div className="coach-shap-bar" aria-hidden="true"><i /><b className={shot.shap[key] >= 0 ? "positive" : "negative"} style={{ left: `${shot.shap[key] >= 0 ? 50 : 50 - Math.abs(shot.shap[key]) / peak * 50}%`, width: `${Math.abs(shot.shap[key]) / peak * 50}%` }} /></div><strong>{shot.shap[key] > 0 ? "+" : ""}{metric(shot.shap[key], 4)}</strong></div>)}</div><div className="coach-reconstruction"><span>Nền {metric(shot.base, 4)} + tổng SHAP {metric(COACH_FEATURES.reduce((sum, key) => sum + shot.shap[key], 0), 4)}</span><strong>Margin {metric(shot.margin, 4)} → sigmoid → xG {metric(shot.xg, 3)}</strong></div><details className="coach-event-id"><summary>Event ID nguồn</summary><code>{shot.id}</code></details></section>
}

export default function CoachReport() {
  const [local, setLocal] = useState<{ report: Report; name: string } | null>(null)
  const [teamId, setTeamId] = useState<number | null>(null)
  const [cardId, setCardId] = useState("")
  const [shotId, setShotId] = useState("")
  const [allShots, setAllShots] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reading, setReading] = useState(false)
  const generation = useRef(0)
  useEffect(() => () => { generation.current++ }, [])
  const example = useQuery({ queryKey: ["coach-demo"], enabled: !local, retry: false, queryFn: async ({ signal }) => {
    const response = await fetch("/coach-demo/advisor.json", { signal })
    if (!response.ok || !response.headers.get("content-type")?.includes("application/json")) throw new Error("Báo cáo mẫu chưa có sẵn. Bạn có thể mở báo cáo advisor đã xử lý.")
    return parseCoachReport(await response.text())
  } })
  const report = local?.report ?? example.data
  const team = report?.teams.find(t => t.id === teamId) ?? report?.teams[0]
  const card = team?.cards.find(c => c.id === cardId) ?? team?.cards[0]
  const shots = (!allShots && card ? card.shots : team?.shots) ?? []
  const shot = shots.find(s => s.id === shotId) ?? shots[0]

  function resetSelection() { setTeamId(null); setCardId(""); setShotId(""); setAllShots(false) }
  async function openFile(file?: File) {
    if (!file) return
    const id = ++generation.current
    setError(null); setReading(false)
    if (file.size > MAX_COACH_BYTES) { setError("File báo cáo vượt giới hạn 10 MB."); return }
    setReading(true)
    try {
      const data = parseCoachReport(await file.text())
      if (id === generation.current) { setLocal({ report: data, name: file.name }); resetSelection() }
    } catch (failure) { if (id === generation.current) setError(failure instanceof Error ? failure.message : "Không đọc được báo cáo.") }
    finally { if (id === generation.current) setReading(false) }
  }
  function download() {
    if (!report) return
    const url = URL.createObjectURL(new Blob([JSON.stringify(report.original, null, 2)], { type: "application/json;charset=utf-8" }))
    const anchor = document.createElement("a")
    anchor.href = url; anchor.download = `coach-report-${report.matchId}.json`; anchor.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  return <div className="coach-page">
    <section className="coach-intro"><div><span className="eyebrow">TỪ SỐ LIỆU ĐẾN ĐIỀU CẦN XEM LẠI</span><h2>Báo cáo HLV</h2><p>Cơ hội dứt điểm, gợi ý rà soát và căn cứ phía sau.</p></div><div className="coach-actions"><label className="coach-file"><FileJson size={15} />{reading ? "Đang đọc…" : "Mở báo cáo JSON"}<input accept=".json,application/json" aria-label="Mở báo cáo JSON" type="file" onChange={event => { void openFile(event.target.files?.[0]); event.target.value = "" }} /></label><Button disabled={!report || reading} onClick={download} variant="outline"><ArrowDownToLine size={15} />Tải JSON</Button></div></section>
    {(error || (!local && example.error)) && <div className="error-notice" role="alert"><AlertCircle size={18} /><span>{error || example.error?.message}</span>{!error && <Button onClick={() => void example.refetch()} variant="outline">Thử lại</Button>}</div>}
    {!local && example.isPending ? <div role="status" className="coach-loading card-surface"><LoaderCircle className="animate-spin" />Đang tải báo cáo…</div> : report ? <>
      <section className="coach-match card-surface"><span className="coach-draft">BẢN NHÁP SAU TRẬN</span><div><h3>{report.teams.map(t => t.name).join(" — ") || "Chưa có dữ liệu đội"}</h3><p>StatsBomb · Trận {report.matchId} · {report.shots.length} cú sút không penalty · Hiệp 1–4</p></div><div className="coach-match-source"><span>{local?.name || "Báo cáo mẫu đã xử lý"}</span>{local && <button onClick={() => { generation.current++; setLocal(null); setReading(false); setError(null); resetSelection() }}>Mở lại mẫu</button>}</div></section>
      <div className="coach-scope-note"><SearchCheck size={17} /><p>Gợi ý để HLV xem lại tình huống, chưa được nghiệm thu hiệu quả chiến thuật. {report.split === "val" ? "Trận này thuộc tập validation của mô hình xG." : report.split === "train" ? "Trận này thuộc tập train của mô hình xG." : report.split === "test" ? "Trận thuộc tập test xG; chất lượng gợi ý HLV vẫn chưa được đánh giá độc lập." : "Chưa rõ phân tập nguồn của trận."}</p></div>
      <div aria-label="Chọn đội trong báo cáo" className="coach-team-tabs">{report.teams.map(t => <button aria-pressed={team?.id === t.id} key={t.id} onClick={() => { setTeamId(t.id); setCardId(""); setShotId(""); setAllShots(false) }}><strong>{t.name}</strong><span>{t.shots.length} cú sút · xG {metric(t.totalXg, 3)}</span></button>)}</div>
      {team ? <>
        <section aria-label="Tổng hợp cơ hội" className="coach-summary card-surface"><div><span>Cú sút hợp lệ</span><strong>{team.shots.length}</strong></div><div><span>Tổng xG dự án</span><strong>{metric(team.totalXg, 3)}</strong></div><div><span>xG trung bình</span><strong>{metric(team.meanXg, 3)}</strong></div><div><span>Gợi ý rà soát</span><strong>{team.cards.length}</strong></div></section>
        <section className="coach-recommendations"><div className="coach-section-heading"><h3><ClipboardList size={17} />Điều cần xem lại</h3><span>Luật cố định + xG + SHAP</span></div>{team.cards.map(c => <article className={`coach-recommendation card-surface${card?.id === c.id ? " selected" : ""}`} key={c.id}><div className="coach-card-number"><Layers size={18} /></div><div className="coach-card-copy"><h4>{c.title}</h4><p>{c.action}</p><div className="coach-card-facts"><span>{c.criterion}</span><span><strong>{c.shots.length}/{team.shots.length}</strong> cú sút ({metric(c.fraction * 100, 1)}%)</span><span>xG nhóm <strong>{metric(c.meanXg, 3)}</strong></span></div><small>Tỷ lệ nhóm làm căn cứ, không phải độ tin cậy của AI.</small><details className="coach-group-evidence"><summary>Xem SHAP trung bình của nhóm</summary><div className="coach-group-row"><span>Feature</span><span>Giá trị TB</span><span>SHAP TB</span></div>{c.support.map(key => <div className="coach-group-row" key={key}><span>{COACH_LABELS[key]}</span><strong>{metric(c.meanFeatures[key], 3)}</strong><strong>{c.meanShap[key] > 0 ? "+" : ""}{metric(c.meanShap[key], 4)}</strong></div>)}<p>SHAP trung bình có đơn vị log-odds, không phải phần trăm cải thiện.</p></details></div><Button aria-pressed={card?.id === c.id && !allShots} onClick={() => { setCardId(c.id); setAllShots(false); setShotId("") }} variant="outline">Xem {c.shots.length} cú sút căn cứ<ArrowUpRight size={14} /></Button></article>)}{!team.cards.length && <div className="coach-empty card-surface">{team.status === "insufficient_data" ? "Chưa đủ cú sút hợp lệ để sinh gợi ý." : "Chưa có luật nào đủ điều kiện. Không có gợi ý không đồng nghĩa đội chơi tốt."}</div>}</section>
        <div className="coach-evidence-grid"><section aria-label="Cú sút làm căn cứ" className="coach-shot-list card-surface"><div className="coach-section-heading"><h3>{allShots || !card ? "Cú sút của đội" : "Cú sút làm căn cứ"}</h3><span>{shots.length} pha</span></div><label className="coach-all-shots"><input type="checkbox" checked={allShots} onChange={event => { setAllShots(event.target.checked); setShotId("") }} />Xem tất cả cú sút của đội</label>{shots.length ? <div className="coach-shot-buttons">{shots.map(s => <button aria-pressed={shot?.id === s.id} key={s.id} onClick={() => setShotId(s.id)}><span className="coach-shot-time">{coachTime(s)}</span><span><strong>{s.shortName}</strong><small>Hiệp {s.period} · #{s.index}</small></span><span className="coach-shot-xg">{metric(s.xg, 3)}<small>xG</small></span></button>)}</div> : <p className="coach-caption">Không có cú sút hợp lệ.</p>}</section><div className="coach-explanation-card card-surface">{shot ? <ShotExplanation shot={shot} /> : <div className="coach-empty">Chọn một cú sút để xem giải thích.</div>}</div></div>
      </> : <div className="coach-empty card-surface">Báo cáo chưa có đội hoặc cú sút để hiển thị.</div>}
      <details className="coach-method card-surface"><summary>Phương pháp, nguồn và giới hạn</summary><p>xG là xác suất cú sút, không phải dự đoán tỷ số. SHAP giải thích mô hình; không chứng minh hiệu quả nhân quả của một thay đổi chiến thuật.</p><p>Mô hình dùng {report.trees} cây tốt nhất; các số liệu và liên kết căn cứ đã được đối chiếu khi đọc file. Mã mô hình: <code>{report.modelHash}</code>.</p><ul>{report.limitations.map((line, i) => <li key={i}>{line}</li>)}</ul></details>
    </> : null}
  </div>
}
