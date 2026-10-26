import { useEffect, useMemo, useRef, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { AlertCircle, ArrowUpRight, FileJson, LoaderCircle, Search, Shield, UserRound, Users } from "lucide-react"
import Pitch from "@/components/Pitch"
import { Button } from "@/components/ui/button"
import { toSvg } from "@/lib/pitchCoordinates"
import { filterPlayers, formatProfileMetric as metric, MAX_PROFILE_BYTES, parsePlayerReport } from "@/lib/playerProfiles"
import type { PlayerProfile, PlayerReport, TrackingStats } from "@/lib/playerProfiles"
import "./playerProfiles.css"

function Metric({ label, value, unit, note }: { label: string; value: number | null; unit?: string; note?: string }) {
  return <div className="profile-metric"><span>{label}</span><strong>{metric(value, unit ? 1 : 0)}{value !== null && unit && <small>{unit}</small>}</strong>{note && <small>{note}</small>}</div>
}

function Heatmap({ tracking }: { tracking: TrackingStats }) {
  const peak = Math.max(0, ...tracking.heatmap.flat())
  const median = tracking.median ? toSvg(...tracking.median) : null
  return <section className="profile-section"><div className="profile-section-heading"><h4>Phân bố vị trí quan sát</h4><span>{metric(tracking.samples)} mẫu</span></div><div className="profile-heatmap"><Pitch>{tracking.heatmap.flatMap((row, y) => row.map((count, x) => count ? <rect key={`${x}:${y}`} x={x * 5} y={68 - (y + 1) * 68 / 14} width="5" height={68 / 14} fill="#fb923c" opacity={.15 + .65 * count / peak}><title>{count} khung quan sát · ô ({x}, {y})</title></rect> : null))}{median && <circle cx={median.x} cy={median.y} r="1.1" fill="white" stroke="#17251c" strokeWidth=".4"><title>Vị trí trung vị quan sát</title></circle>}</Pitch></div><p className="profile-caption">Ô sáng hơn = nhiều khung quan sát hơn trong hồ sơ này. Điểm trắng là vị trí trung vị; không phải vị trí chiến thuật được nhận diện.</p></section>
}

function EventDetail({ player }: { player: PlayerProfile }) {
  const [kind, setKind] = useState<"Pass" | "Carry" | "Shot">("Pass")
  const [expanded, setExpanded] = useState(false)
  const stats = player.events!
  const indices = stats.indices[kind]
  return <>
    <div className="profile-metrics"><Metric label="Đường chuyền" value={stats.passes} /><Metric label="Hoàn thành" value={stats.completionPct} unit="%" note={`${metric(stats.completed)} / ${metric(stats.passes)} đường chuyền`} /><Metric label="Cú sút" value={stats.shots} /><Metric label="Cú sút thành bàn" value={stats.goals} note="Không gồm phản lưới nhà" /></div>
    <div className="profile-secondary"><span><strong>{metric(stats.carries)}</strong> sự kiện Carry</span><span><strong>{metric(stats.events)}</strong> sự kiện ghi nhận</span></div>
    <section className="profile-section"><div className="profile-section-heading"><h4>Ngữ cảnh vai trò từ nguồn</h4><span>Theo index sự kiện</span></div>{stats.roles.length ? <div className="profile-table-scroll"><table className="profile-role-table"><thead><tr><th>Trạng thái</th><th>Vị trí / sơ đồ</th><th>Index</th><th>Sự kiện</th></tr></thead><tbody>{stats.roles.map((role, index) => <tr key={index}><td><span className={`role-status ${role.status}`}>{role.status === "reference" ? "Tham chiếu" : "Chưa xác định"}</span></td><td>{role.position || "—"}<small>{role.shape || "Chưa có tham chiếu hợp lệ"}</small></td><td>{role.first}–{role.last}</td><td>{role.count}</td></tr>)}</tbody></table></div> : <p className="profile-caption">Chưa có sự kiện để hiển thị ngữ cảnh vai trò.</p>}</section>
    <section className="profile-section"><div className="profile-section-heading"><h4>Tra cứu sự kiện nguồn</h4><span>Không phải thời gian thi đấu</span></div><div aria-label="Loại sự kiện" className="profile-event-tabs">{(["Pass", "Carry", "Shot"] as const).map(key => <button aria-pressed={kind === key} key={key} onClick={() => { setKind(key); setExpanded(false) }}>{key} <span>{stats.indices[key].length}</span></button>)}</div>{indices.length ? <div className="profile-event-indices">{(expanded ? indices : indices.slice(0, 24)).map(index => <span key={index}>#{index}</span>)}</div> : <p className="profile-caption">Không có sự kiện {kind} được ghi nhận.</p>}{indices.length > 24 && <button className="profile-text-button" onClick={() => setExpanded(!expanded)}>{expanded ? "Thu gọn" : `Xem toàn bộ ${indices.length} index`}</button>}</section>
    <p className="profile-footnote">Số sự kiện không phải số lần chạm bóng hoặc phút thi đấu. Vai trò là tham chiếu từ dữ liệu, không xác nhận vị trí chiến thuật thực tế; Shot Goal không phải tỷ số trận.</p>
  </>
}

function TrackingDetail({ player }: { player: PlayerProfile }) {
  const stats = player.tracking!
  return <>
    <div className="profile-metrics"><Metric label="Quãng đường quan sát" value={stats.distance} unit="m" /><Metric label="Tốc độ trung bình" value={stats.meanSpeed} unit="km/h" /><Metric label="Tốc độ cao nhất" value={stats.maxSpeed} unit="km/h" /><Metric label="Thời gian đại diện" value={stats.represented} unit="s" /></div>
    <section className="profile-section"><div className="profile-section-heading"><h4>Mức độ bao phủ dữ liệu</h4><span>{metric(stats.rejected)} khoảng vượt ngưỡng bị loại</span></div>{[["Khung có vị trí", stats.coverage], ["Thời gian chuyển động được nhận", stats.representedFraction]].map(([label, fraction]) => <div className="coverage-line" key={label}><div><span>{label}</span><strong>{metric(Number(fraction) * 100, 1)}%</strong></div><progress aria-label={String(label)} max="1" value={Number(fraction)} /></div>)}</section>
    <Heatmap tracking={stats} />
    <p className="profile-footnote">Chỉ số chỉ thuộc cửa sổ được ghi ở trên, không phải toàn trận. Không nối qua khoảng mất dữ liệu hoặc ngoại suy lên 90 phút. Tốc độ lớn nhất tính trên khoảng lấy mẫu, không phải tốc độ tức thời. Đây là dữ liệu Metrica, không phải phép đo từ video của bạn.</p>
  </>
}

export default function PlayerProfiles() {
  const [source, setSource] = useState<"statsbomb" | "metrica">("statsbomb")
  const [local, setLocal] = useState<{ report: PlayerReport; name: string } | null>(null)
  const [team, setTeam] = useState("")
  const [search, setSearch] = useState("")
  const [selected, setSelected] = useState("")
  const [fileError, setFileError] = useState<string | null>(null)
  const [reading, setReading] = useState(false)
  const generation = useRef(0)
  useEffect(() => () => { generation.current++ }, [])
  const demo = useQuery({ queryKey: ["player-demo", source], enabled: !local, retry: false, queryFn: async ({ signal }) => {
    const response = await fetch(`/player-demo/${source}.json`, { signal })
    if (!response.ok || !response.headers.get("content-type")?.includes("application/json")) throw new Error("Dữ liệu mẫu chưa có sẵn. Bạn có thể mở file hồ sơ đã xử lý.")
    return parsePlayerReport(await response.text())
  } })
  const report = local?.report ?? demo.data
  const visible = useMemo(() => report ? filterPlayers(report, team, search) : [], [report, team, search])
  const player = visible.find(p => p.key === selected) ?? visible[0]

  function resetFilters() { setTeam(""); setSearch(""); setSelected("") }
  function chooseSource(next: "statsbomb" | "metrica") { generation.current++; setSource(next); setLocal(null); setFileError(null); setReading(false); resetFilters() }
  async function openFile(file?: File) {
    if (!file) return
    const id = ++generation.current
    setFileError(null)
    setReading(false)
    if (file.size > MAX_PROFILE_BYTES) { setFileError("File hồ sơ vượt giới hạn 5 MB."); return }
    setReading(true)
    try {
      const parsed = parsePlayerReport(await file.text())
      if (id !== generation.current) return
      setLocal({ report: parsed, name: file.name }); resetFilters()
    } catch (error) { if (id === generation.current) setFileError(error instanceof Error ? error.message : "Không đọc được file hồ sơ.") }
    finally { if (id === generation.current) setReading(false) }
  }

  return <div className="players-page">
    <section className="players-intro"><div><span className="eyebrow">CON NGƯỜI SAU NHỮNG CON SỐ</span><h2>Hồ sơ cầu thủ</h2><p>Đọc đóng góp trong trận, bắt đầu từ dữ liệu có căn cứ.</p></div><label className="profile-open-file"><FileJson size={16} />{reading ? "Đang đọc…" : "Mở hồ sơ JSON"}<input accept=".json,application/json" aria-label="Mở hồ sơ JSON" onChange={event => { void openFile(event.target.files?.[0]); event.target.value = "" }} type="file" /></label></section>
    <section aria-label="Nguồn hồ sơ" className="profile-source-bar card-surface"><div className="profile-source-buttons"><button aria-pressed={!local && source === "statsbomb"} onClick={() => chooseSource("statsbomb")}>StatsBomb <small>Sự kiện trận đấu</small></button><button aria-pressed={!local && source === "metrica"} onClick={() => chooseSource("metrica")}>Metrica <small>Chuyển động & heatmap</small></button></div><div className="profile-source-context"><strong>{local ? local.name : report?.label || "Đang tải hồ sơ…"}</strong><span>{report?.scope || ""}</span></div></section>
    {(fileError || (!local && demo.error)) && <div className="error-notice" role="alert"><AlertCircle size={18} /><span>{fileError || demo.error?.message}</span>{!fileError && <Button onClick={() => void demo.refetch()} variant="outline">Thử lại</Button>}</div>}
    {!local && demo.isPending ? <div className="profile-loading card-surface" role="status"><LoaderCircle className="animate-spin" />Đang tải hồ sơ cầu thủ…</div> : report ? <div className="players-layout">
      <aside aria-label="Danh sách cầu thủ" className="player-directory card-surface"><div className="directory-title"><h3><Users size={17} />Cầu thủ</h3><span>{visible.length} / {report.players.length}</span></div><label className="player-search"><Search size={15} /><input aria-label="Tìm cầu thủ" onChange={event => setSearch(event.target.value)} placeholder="Tìm tên hoặc ID…" type="search" value={search} /></label><label className="player-team-filter">Đội<select aria-label="Lọc theo đội" onChange={event => { setTeam(event.target.value); setSelected("") }} value={team}><option value="">Tất cả đội</option>{report.teams.map(name => <option key={name} value={name}>{name}</option>)}</select></label><div className="player-list">{visible.map(p => <button aria-pressed={player?.key === p.key} className="player-list-row" key={p.key} onClick={() => setSelected(p.key)}><span className="player-list-avatar">{p.jersey ?? (p.tracking ? p.id : "—")}</span><span><strong>{p.shortName}</strong><small>{p.team}{p.starter === true ? " · Xuất phát" : p.goalkeeper ? " · Thủ môn" : ""}</small></span><ArrowUpRight aria-hidden="true" size={14} /></button>)}{!visible.length && <p className="directory-empty">Không tìm thấy cầu thủ phù hợp.</p>}</div></aside>
      <section aria-label="Hồ sơ đang chọn" className="player-detail card-surface">{player ? <><header className="player-identity"><span className="player-identity-avatar">{player.jersey ?? <UserRound size={30} />}</span><div><span className="eyebrow">{report.source === "statsbomb" ? "STATSBOMB · SỰ KIỆN" : "METRICA · TRACKING"}</span><h3>{player.shortName}</h3><p>{player.name}</p><div className="player-identity-tags"><span><Shield size={12} />{player.team}</span><span>ID {player.id}</span>{player.starter !== null && <span>{player.starter ? "Đội hình xuất phát" : "Không xuất phát"}</span>}{player.goalkeeper && <span>Thủ môn</span>}</div></div></header><div className="player-scope-label">{report.label} <span>· {report.scope}</span></div>{player.events ? <EventDetail key={player.key} player={player} /> : <TrackingDetail key={player.key} player={player} />}</> : <div className="profile-no-selection"><UserRound size={32} /><h3>{report.players.length ? "Chưa có cầu thủ phù hợp" : "Báo cáo chưa có hồ sơ"}</h3><p>{report.players.length ? "Thử đổi đội hoặc từ khóa tìm kiếm." : "Mở báo cáo khác để xem dữ liệu."}</p></div>}</section>
    </div> : null}
  </div>
}
