import { useEffect, useReducer, useRef, useState } from "react"
import type { PointerEvent as ReactPointerEvent } from "react"
import { ArrowUpRight, CircleDot, Download, Eraser, FileJson, MousePointer2, MoveUpRight, Play, Plus, RectangleHorizontal, Redo2, Save, Square, Trash2, Type, Undo2, Upload, UserRound, Waypoints } from "lucide-react"
import Pitch from "@/components/Pitch"
import { toSvg } from "@/lib/pitchCoordinates"
import { applyFormation, BOARD_STORAGE_KEY, boardReducer, clampPoint, FORMATIONS, initialBoard, MAX_BOARD_BYTES, parseTacticsBoard, storeTacticsBoard, translateObject } from "@/lib/tacticsBoard"
import type { BoardObject, BoardPhase, BoardTeam, ObjectType, TacticsBoard as Board } from "@/lib/tacticsBoard"
import "./tacticsBoard.css"

type Tool = "select" | "erase" | ObjectType
const TOOLS = [
  { id: "select", label: "Chọn", icon: MousePointer2 }, { id: "player", label: "Cầu thủ", icon: UserRound },
  { id: "ball", label: "Bóng", icon: CircleDot }, { id: "pass", label: "Chuyền", icon: ArrowUpRight },
  { id: "run", label: "Chạy", icon: MoveUpRight }, { id: "zone", label: "Vùng", icon: RectangleHorizontal },
  { id: "text", label: "Chữ", icon: Type }, { id: "erase", label: "Xóa", icon: Eraser },
] as const
type Gesture = { pointer: number; phaseId: string; start: { x_m: number; y_m: number }; object: BoardObject; mode: "move" | "draw" }

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob), anchor = document.createElement("a")
  anchor.href = url; anchor.download = filename; anchor.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

function BoardMark({ object, color, selected, onFocus }: { object: BoardObject; color: string; selected: boolean; onFocus: () => void }) {
  const point = toSvg(object.x_m, object.y_m)
  const end = toSvg(object.end_x_m ?? object.x_m, object.end_y_m ?? object.y_m)
  const name = object.type === "player" ? `Đội ${object.team} · cầu thủ ${object.number}${object.label ? ` · ${object.label}` : ""}` : `${TOOLS.find(tool => tool.id === object.type)?.label} đội ${object.team}`
  return <g data-board-id={object.id} role="button" aria-label={name} aria-pressed={selected} tabIndex={0} onFocus={onFocus} className="tactics-object">
    {object.type === "player" ? <>
      <circle cx={point.x} cy={point.y + .35} r={2.05} fill="#001f1b" opacity={.4} />
      <circle cx={point.x} cy={point.y} r={1.95} fill={color} stroke="#ffffffc9" strokeWidth={.32} />
      <circle cx={point.x - .5} cy={point.y - .65} r={.65} fill="white" opacity={.12} />
      <text x={point.x} y={point.y + .07} textAnchor="middle" dominantBaseline="central" fill="white" fontSize={1.65} fontWeight={700} fontFamily="Arial, sans-serif" pointerEvents="none">{object.number}</text>
      {object.label && <text x={point.x} y={point.y + 3.45} textAnchor="middle" fill="white" stroke="#09291f" strokeWidth={.5} paintOrder="stroke" fontSize={1.2} fontFamily="Arial, sans-serif" pointerEvents="none">{object.label}</text>}
      {selected && <circle data-editor-only="true" cx={point.x} cy={point.y} r={2.6} stroke="#fde68a" strokeWidth={.3} fill="none" />}
    </> : object.type === "ball" ? <>
      <circle cx={point.x} cy={point.y} r={1.25} fill="#f8fafc" stroke="#0b1e22" strokeWidth={.25} />
      <path d={`M ${point.x} ${point.y - .65} l .6 .42 -.23 .72 h -.74 l -.23 -.72 Z`} fill="#18242c" />
      {selected && <circle data-editor-only="true" cx={point.x} cy={point.y} r={1.8} stroke="#fde68a" strokeWidth={.3} fill="none" />}
    </> : object.type === "text" ? <>
      <text x={point.x} y={point.y} fill={color} stroke="#0c281f" strokeWidth={.65} paintOrder="stroke" fontSize={2} fontWeight={600} fontFamily="Arial, sans-serif">{object.label || "Ghi chú"}</text>
      {selected && <circle data-editor-only="true" cx={point.x} cy={point.y} r={.65} fill="#fde68a" />}
    </> : object.type === "zone" ? <>
      <rect x={Math.min(point.x, end.x)} y={Math.min(point.y, end.y)} width={Math.abs(end.x - point.x)} height={Math.abs(end.y - point.y)} fill={color} fillOpacity={.18} stroke={color} strokeWidth={.45} strokeDasharray="1 .8" />
      {selected && <rect data-editor-only="true" x={Math.min(point.x, end.x)} y={Math.min(point.y, end.y)} width={Math.abs(end.x - point.x)} height={Math.abs(end.y - point.y)} fill="none" stroke="#fde68a" strokeWidth={.3} />}
    </> : <>
      <line x1={point.x} y1={point.y} x2={end.x} y2={end.y} stroke="transparent" strokeWidth={3} />
      <line x1={point.x} y1={point.y} x2={end.x} y2={end.y} stroke={color} strokeWidth={.48} strokeDasharray={object.type === "run" ? "1.4 1" : undefined} markerEnd={`url(#board-arrow-${object.team})`} />
      {selected && <><circle data-editor-only="true" cx={point.x} cy={point.y} r={.7} fill="#fde68a" /><circle data-editor-only="true" cx={end.x} cy={end.y} r={.7} fill="#fde68a" /></>}
    </>}
  </g>
}

export default function TacticsBoard() {
  const [loaded] = useState(() => {
    try { const raw = localStorage.getItem(BOARD_STORAGE_KEY); return { board: raw ? parseTacticsBoard(raw) : initialBoard(), error: "", canSave: true } }
    catch { return { board: initialBoard(), error: "Chưa đọc được bảng đã lưu. Bản cũ được giữ; chọn Lưu trên máy khi muốn lưu bảng hiện tại.", canSave: false } }
  })
  const [history, dispatch] = useReducer(boardReducer, { past: [], present: loaded.board, future: [] })
  const board = history.present
  const [phaseId, setPhaseId] = useState(board.phases[0].id)
  const phase = board.phases.find(item => item.id === phaseId) ?? board.phases[0]
  const [team, setTeam] = useState<BoardTeam>("A")
  const [tool, setTool] = useState<Tool>("select")
  const [selectedId, setSelectedId] = useState("")
  const selected = phase.objects.find(object => object.id === selectedId)
  const [preview, setPreview] = useState<BoardObject | null>(null)
  const [playing, setPlaying] = useState(false)
  const [notice, setNotice] = useState(loaded.error)
  const [saveResult, setSaveResult] = useState<{ board: Board; status: string } | null>(null)
  const [canSave, setCanSave] = useState(loaded.canSave)
  const pendingSave = useRef({ board, canSave })
  const [exporting, setExporting] = useState(false)
  const [pngPreview, setPngPreview] = useState<{ url: string; blob: Blob; name: string } | null>(null)
  const exportDialog = useRef<HTMLDialogElement | null>(null)
  const [lanes, setLanes] = useState(false)
  const svg = useRef<SVGSVGElement | null>(null)
  const gesture = useRef<Gesture | null>(null)
  const importGeneration = useRef(0)
  useEffect(() => () => { importGeneration.current++ }, [])
  useEffect(() => () => {
    if (pendingSave.current.canSave) {
      try { storeTacticsBoard(localStorage, pendingSave.current.board) } catch { /* Keep the last successfully saved board. */ }
    }
  }, [])
  useEffect(() => {
    if (!pngPreview) return
    exportDialog.current?.showModal()
    return () => URL.revokeObjectURL(pngPreview.url)
  }, [pngPreview])
  const commit = (next: Board) => dispatch({ type: "commit", board: next })
  const updatePhase = (next: BoardPhase) => commit({ ...board, phases: board.phases.map(item => item.id === next.id ? next : item) })

  useEffect(() => {
    pendingSave.current = { board, canSave }
    if (!canSave) return
    function saveBoard() {
      try {
        storeTacticsBoard(localStorage, board); setSaveResult({ board, status: "Đã lưu trên trình duyệt" })
      } catch { setSaveResult({ board, status: "Chưa lưu trên máy" }); setNotice("Không lưu được bảng trên trình duyệt. Bạn vẫn có thể tải JSON để giữ bản đang mở.") }
    }
    const timer = window.setTimeout(saveBoard, 400)
    window.addEventListener("pagehide", saveBoard)
    return () => { window.clearTimeout(timer); window.removeEventListener("pagehide", saveBoard) }
  }, [board, canSave])
  useEffect(() => {
    if (!playing) return
    const timer = window.setTimeout(() => {
      const index = board.phases.findIndex(item => item.id === phase.id)
      if (index >= board.phases.length - 1) setPlaying(false)
      else { setPhaseId(board.phases[index + 1].id); setSelectedId("") }
    }, 1400)
    return () => window.clearTimeout(timer)
  }, [playing, board.phases, phase.id])
  useEffect(() => {
    function keys(event: KeyboardEvent) {
      if (pngPreview) return
      if ((event.target as HTMLElement).closest("input, textarea, select, [contenteditable=true]")) return
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
        event.preventDefault(); setPlaying(false); dispatch({ type: event.shiftKey ? "redo" : "undo" }); return
      }
      if (playing) return
      if (event.key === "Escape") { gesture.current = null; setPreview(null); setSelectedId(""); setTool("select") }
      if (!selected) return
      if (event.key === "Delete" || event.key === "Backspace") {
        event.preventDefault(); updatePhase({ ...phase, objects: phase.objects.filter(object => object.id !== selected.id) }); setSelectedId("")
      }
      const movement: Record<string, [number, number]> = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, 1], ArrowDown: [0, -1] }
      if (event.key in movement) {
        event.preventDefault(); const [dx, dy] = movement[event.key], scale = event.shiftKey ? 3 : .5
        updatePhase({ ...phase, objects: phase.objects.map(object => object.id === selected.id ? translateObject(object, dx * scale, dy * scale) : object) })
      }
    }
    window.addEventListener("keydown", keys)
    return () => window.removeEventListener("keydown", keys)
  })

  function pointAt(event: ReactPointerEvent<SVGSVGElement>) {
    const matrix = svg.current?.getScreenCTM()
    if (!matrix) return null
    const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse())
    return clampPoint(point.x, 68 - point.y)
  }
  function pointerDown(event: ReactPointerEvent<SVGSVGElement>) {
    if (playing || event.button !== 0 || gesture.current) return
    const point = pointAt(event)
    if (!point) return
    event.preventDefault(); svg.current?.focus()
    const id = (event.target as Element).closest("[data-board-id]")?.getAttribute("data-board-id")
    const object = phase.objects.find(item => item.id === id)
    if (tool === "erase") {
      if (object) updatePhase({ ...phase, objects: phase.objects.filter(item => item.id !== object.id) })
      setSelectedId(""); return
    }
    if (tool === "select") {
      setSelectedId(object?.id ?? "")
      if (!object) return
      gesture.current = { pointer: event.pointerId, phaseId: phase.id, start: point, object, mode: "move" }
    } else {
      if (phase.objects.length >= 150) { setNotice("Mỗi pha có tối đa 150 đối tượng."); return }
      const next: BoardObject = { id: crypto.randomUUID(), type: tool, team, ...point, label: tool === "text" ? "Điểm hỗ trợ" : "", ...(tool === "player" ? { number: Math.min(99, 1 + phase.objects.filter(item => item.type === "player" && item.team === team).length) } : {}) }
      if (["pass", "run", "zone"].includes(tool)) {
        next.end_x_m = point.x_m; next.end_y_m = point.y_m
        gesture.current = { pointer: event.pointerId, phaseId: phase.id, start: point, object: next, mode: "draw" }
        setPreview(next)
      } else {
        const objects = tool === "ball" ? phase.objects.filter(item => item.type !== "ball") : phase.objects
        updatePhase({ ...phase, objects: [...objects, next] }); setSelectedId(next.id); setTool("select"); return
      }
    }
    svg.current?.setPointerCapture(event.pointerId)
  }
  function gestureObject(current: Gesture, point: { x_m: number; y_m: number }) {
    return current.mode === "move" ? translateObject(current.object, point.x_m - current.start.x_m, point.y_m - current.start.y_m) : { ...current.object, end_x_m: point.x_m, end_y_m: point.y_m }
  }
  function pointerMove(event: ReactPointerEvent<SVGSVGElement>) {
    const current = gesture.current, point = pointAt(event)
    if (current && point && current.pointer === event.pointerId) setPreview(gestureObject(current, point))
  }
  function pointerUp(event: ReactPointerEvent<SVGSVGElement>) {
    const current = gesture.current, point = pointAt(event)
    if (!current || current.pointer !== event.pointerId) return
    gesture.current = null; setPreview(null)
    if (svg.current?.hasPointerCapture(event.pointerId)) svg.current.releasePointerCapture(event.pointerId)
    if (!point || current.phaseId !== phase.id) return
    const next = gestureObject(current, point)
    if (current.mode === "draw" && Math.hypot(point.x_m - current.start.x_m, point.y_m - current.start.y_m) < 1) return
    updatePhase({ ...phase, objects: current.mode === "move" ? phase.objects.map(item => item.id === next.id ? next : item) : [...phase.objects, next] })
    setSelectedId(next.id)
  }
  function updateSelected(fields: Partial<BoardObject>) {
    if (selected) updatePhase({ ...phase, objects: phase.objects.map(object => object.id === selected.id ? { ...object, ...fields } : object) })
  }
  function addPhase() {
    if (board.phases.length >= 8) return
    const next = { ...phase, id: crypto.randomUUID(), name: `Pha ${board.phases.length + 1}`, objects: phase.objects.map(object => ({ ...object })) }
    commit({ ...board, phases: [...board.phases, next] }); setPhaseId(next.id); setSelectedId("")
  }
  async function openBoard(file?: File) {
    if (!file) return
    const generation = ++importGeneration.current
    setPlaying(false)
    try {
      if (file.size > MAX_BOARD_BYTES) throw new Error("File bảng chiến thuật vượt giới hạn 1 MB.")
      const next = parseTacticsBoard(await file.text())
      if (generation !== importGeneration.current) return
      commit(next); setPhaseId(next.phases[0].id); setSelectedId(""); setPreview(null); gesture.current = null; setNotice("")
    } catch (error) { if (generation === importGeneration.current) setNotice(error instanceof Error ? error.message : "Không đọc được bảng chiến thuật.") }
  }
  async function exportPng() {
    if (!svg.current) return
    setExporting(true)
    let url = ""
    try {
      const clone = svg.current.cloneNode(true) as SVGSVGElement
      clone.querySelectorAll("[data-editor-only]").forEach(element => element.remove())
      clone.setAttribute("xmlns", "http://www.w3.org/2000/svg"); clone.setAttribute("width", "1680"); clone.setAttribute("height", "1088")
      url = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(clone)], { type: "image/svg+xml;charset=utf-8" }))
      const image = new Image()
      await new Promise<void>((resolve, reject) => { image.onload = () => resolve(); image.onerror = () => reject(new Error("Không dựng được ảnh sân.")); image.src = url })
      const canvas = document.createElement("canvas"); canvas.width = 1680; canvas.height = 1088
      const context = canvas.getContext("2d")
      if (!context) throw new Error("Trình duyệt không hỗ trợ xuất ảnh.")
      context.drawImage(image, 0, 0, 1680, 1088)
      const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob(value => value ? resolve(value) : reject(new Error("Không xuất được ảnh PNG.")), "image/png"))
      setPngPreview({ url: URL.createObjectURL(blob), blob, name: `touchline-${phase.id}.png` })
    } catch (error) { setNotice(error instanceof Error ? error.message : "Không xuất được PNG.") }
    finally { if (url) URL.revokeObjectURL(url); setExporting(false) }
  }

  const objects = phase.objects.map(object => preview?.id === object.id ? preview : object)
  if (preview && !objects.some(object => object.id === preview.id)) objects.push(preview)
  const ordered = [...objects.filter(object => ["zone", "pass", "run"].includes(object.type)), ...objects.filter(object => !["zone", "pass", "run"].includes(object.type))]
  return <div className="tactics-page">
    {pngPreview && <dialog ref={exportDialog} className="tactics-png-dialog" aria-label="Ảnh bảng chiến thuật" onCancel={event => { event.preventDefault(); setPngPreview(null) }}>
      <div><h3>Ảnh bảng chiến thuật</h3><button aria-label="Đóng ảnh xem trước" onClick={() => setPngPreview(null)}>×</button></div>
      <img src={pngPreview.url} alt="Bản PNG của pha chiến thuật đang chọn" />
      <footer><span>PNG · 1680 × 1088 · Pha {phase.name}</span><button onClick={() => downloadBlob(pngPreview.blob, pngPreview.name)}><Download size={15} />Tải ảnh PNG</button></footer>
    </dialog>}
    <header className="tactics-header">
      <div className="tactics-heading"><span className="tactics-logo"><Waypoints size={23} /></span><div><span className="eyebrow">TOUCHLINE · COACH STUDIO</span><h2>Bảng chiến thuật</h2></div></div>
      <label className="tactics-title">TÊN BUỔI TẬP<input maxLength={100} value={board.title} disabled={playing} onChange={event => commit({ ...board, title: event.target.value })} /></label>
      <div className="tactics-header-actions">
        <span className="tactics-save-status" role="status">{!canSave ? "Chưa lưu trên máy" : saveResult?.board === board ? saveResult.status : "Đang lưu…"}</span>
        <button title="Hoàn tác (Ctrl+Z)" aria-label="Hoàn tác" disabled={!history.past.length || playing} onClick={() => dispatch({ type: "undo" })}><Undo2 size={16} /></button>
        <button title="Làm lại (Ctrl+Shift+Z)" aria-label="Làm lại" disabled={!history.future.length || playing} onClick={() => dispatch({ type: "redo" })}><Redo2 size={16} /></button>
        <button title="Lưu trên trình duyệt" aria-label="Lưu trên máy" onClick={() => { try { storeTacticsBoard(localStorage, board); setCanSave(true); setSaveResult({ board, status: "Đã lưu trên trình duyệt" }); setNotice("") } catch { setNotice("Không lưu được. Hãy tải JSON để giữ bản hiện tại.") } }}><Save size={16} /></button>
        <button title="Tải file chỉnh sửa" aria-label="Tải bảng JSON" onClick={() => downloadBlob(new Blob([JSON.stringify(board, null, 2)], { type: "application/json" }), "touchline-tactics.json")}><FileJson size={16} /></button>
        <label className="tactics-import" title="Mở bảng JSON"><Upload size={16} /><input aria-label="Mở bảng JSON" type="file" accept=".json,application/json" onChange={event => { void openBoard(event.target.files?.[0]); event.target.value = "" }} /></label>
        <button className="tactics-export" disabled={exporting || playing || !!preview} onClick={() => void exportPng()}><Download size={15} />{exporting ? "Đang xuất…" : "Xuất PNG"}</button>
      </div>
    </header>
    {notice && <div className="tactics-notice" role="alert">{notice}<button aria-label="Đóng thông báo" onClick={() => setNotice("")}>×</button></div>}
    <div className="tactics-workspace">
      <aside className="tactics-tools" aria-label="Công cụ bảng chiến thuật">{TOOLS.map(({ id, label, icon: Icon }) => <button key={id} title={label} aria-label={label} aria-pressed={tool === id} disabled={playing} onClick={() => { setTool(id); setPreview(null); gesture.current = null }}><Icon size={18} /><span>{label}</span></button>)}</aside>
      <section className="tactics-main">
        <div className="tactics-pitch-heading"><div><span className="tactics-full-pitch">Toàn sân</span><span>105 × 68 m</span><button aria-label="Làm trống pha" title="Làm trống pha (có thể hoàn tác)" disabled={playing || !phase.objects.length} onClick={() => { updatePhase({ ...phase, objects: [] }); setSelectedId("") }}><Trash2 size={14} /></button></div><span>{playing ? "Đang trình chiếu các pha" : tool === "select" ? "Kéo để di chuyển · Phím mũi tên · Del để xóa" : tool === "pass" || tool === "run" || tool === "zone" ? "Kéo trên sân để vẽ" : "Chạm trên sân để đặt đối tượng"}</span></div>
        <div className={`tactics-pitch-frame tool-${tool}`}>
          <Pitch className="tactics-pitch" svgProps={{ ref: svg, role: "group", "aria-label": "Sân chiến thuật tương tác", tabIndex: 0, onPointerDown: pointerDown, onPointerMove: pointerMove, onPointerUp: pointerUp, onPointerCancel: () => { gesture.current = null; setPreview(null) } }}>
            <defs>{(["A", "B"] as const).map(side => <marker id={`board-arrow-${side}`} key={side} viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 Z" fill={board.colors[side]} /></marker>)}</defs>
            {lanes && <g pointerEvents="none" stroke="white" strokeOpacity={.2} strokeWidth={.2} strokeDasharray="1 1">{[13.6, 27.2, 40.8, 54.4].map(y => <line key={y} x1={0} x2={105} y1={y} y2={y} />)}</g>}
            <text x={2} y={3} fill="#d4eddf" opacity={.7} fontFamily="Arial, sans-serif" fontSize={1.1} fontWeight={700}>TOUCHLINE • COACH STUDIO</text>
            <text x={52.5} y={66.5} textAnchor="middle" fill="white" opacity={.25} fontFamily="Arial, sans-serif" fontSize={1}>KẾ HOẠCH HUẤN LUYỆN · BỐ TRÍ THỦ CÔNG</text>
            {ordered.map(object => <BoardMark key={object.id} object={object} color={board.colors[object.team]} selected={selectedId === object.id && !playing} onFocus={() => setSelectedId(object.id)} />)}
          </Pitch>
        </div>
        <div className="tactics-phases"><button className="tactics-play" aria-label={playing ? "Dừng trình chiếu" : "Trình chiếu các pha"} disabled={board.phases.length < 2} onClick={() => { if (!playing) setPhaseId(board.phases[0].id); setPlaying(!playing); setSelectedId("") }}>{playing ? <Square size={15} /> : <Play size={15} />}</button><div className="tactics-phase-list">{board.phases.map((item, index) => <button key={item.id} aria-pressed={phase.id === item.id} disabled={playing} onClick={() => { setPhaseId(item.id); setSelectedId("") }}><b>{String(index + 1).padStart(2, "0")}</b><span>{item.name || `Pha ${index + 1}`}</span></button>)}</div><button disabled={board.phases.length >= 8 || playing} onClick={addPhase}><Plus size={15} />Thêm pha</button><button aria-label="Xóa pha đang chọn" disabled={board.phases.length < 2 || playing} onClick={() => { commit({ ...board, phases: board.phases.filter(item => item.id !== phase.id) }); setSelectedId("") }}><Trash2 size={15} /></button></div>
        <p className="tactics-local-note"><i />Lưu tại trình duyệt · Tải JSON để tiếp tục chỉnh sửa trên máy khác · Tối đa 8 pha</p>
      </section>
      <aside className="tactics-inspector" aria-label="Thiết lập chiến thuật">
        <div className="tactics-panel-title">ĐỘI HÌNH & KẾ HOẠCH</div>
        <section><h3>Đội đang chỉnh</h3><p>Chọn đội để thêm hoặc đổi sơ đồ.</p><div className="tactics-team-switch">{(["A", "B"] as const).map(side => <button key={side} aria-pressed={team === side} onClick={() => setTeam(side)}><i style={{ background: board.colors[side] }} />Đội {side}</button>)}</div></section>
        <section><h3>Thư viện sơ đồ</h3><p>Áp dụng cho đội {team} trong pha hiện tại.</p><div className="tactics-formations">{FORMATIONS.map(shape => <button disabled={playing} key={shape} aria-pressed={phase.formations[team] === shape} onClick={() => { updatePhase(applyFormation(phase, team, shape)); setSelectedId("") }}>{shape}</button>)}</div></section>
        <section><h3>Đối tượng đang chọn</h3>{selected ? <div className="tactics-selected-editor"><span className="tactics-object-kind">{TOOLS.find(item => item.id === selected.type)?.label} · Đội {selected.team}</span>{selected.type === "player" && <label>Số áo<input aria-label="Số áo" type="number" min={1} max={99} value={selected.number} disabled={playing} onChange={event => { const n = Number(event.target.value); if (Number.isInteger(n) && n >= 1 && n <= 99) updateSelected({ number: n }) }} /></label>}{(selected.type === "player" || selected.type === "text") && <label>{selected.type === "text" ? "Nội dung" : "Tên / vai trò"}<input aria-label={selected.type === "text" ? "Nội dung nhãn" : "Tên cầu thủ"} value={selected.label} maxLength={60} disabled={playing} onChange={event => updateSelected({ label: event.target.value })} /></label>}<small>x {selected.x_m.toFixed(1)} m · y {selected.y_m.toFixed(1)} m</small><button disabled={playing} onClick={() => { updatePhase({ ...phase, objects: phase.objects.filter(object => object.id !== selected.id) }); setSelectedId("") }}><Trash2 size={13} />Xóa đối tượng</button></div> : <div className="tactics-empty-selection"><MousePointer2 size={24} /><p>Chọn cầu thủ, bóng hoặc nét vẽ trên sân để chỉnh sửa.</p></div>}</section>
        <section><h3>Hiển thị</h3><div className="tactics-colors">{(["A", "B"] as const).map(side => <label key={side}>Màu đội {side}<input aria-label={`Màu đội ${side}`} type="color" value={board.colors[side]} disabled={playing} onChange={event => commit({ ...board, colors: { ...board.colors, [side]: event.target.value } })} /></label>)}</div><label className="tactics-checkbox"><input type="checkbox" checked={lanes} onChange={event => setLanes(event.target.checked)} />Hiện 5 hành lang dọc</label></section>
        <section><h3>Kế hoạch của pha</h3><label>Tên pha<input aria-label="Tên pha" value={phase.name} maxLength={80} disabled={playing} onChange={event => updatePhase({ ...phase, name: event.target.value })} /></label><label>Ghi chú cho HLV<textarea aria-label="Ghi chú chiến thuật" value={phase.notes} maxLength={4000} rows={4} disabled={playing} placeholder="Ví dụ: tiền vệ trụ lùi nhận bóng, hậu vệ biên mở rộng…" onChange={event => updatePhase({ ...phase, notes: event.target.value })} /></label></section>
        <section><h3>Đối tượng trong pha ({phase.objects.length})</h3><div className="tactics-object-list">{phase.objects.map(object => <button key={object.id} aria-pressed={selectedId === object.id} onClick={() => { setSelectedId(object.id); setTool("select") }}>{object.type === "player" ? `Đội ${object.team} · #${object.number} ${object.label}` : `${TOOLS.find(item => item.id === object.type)?.label} · ${object.label || `Đội ${object.team}`}`}</button>)}</div></section>
      </aside>
    </div>
  </div>
}
