export const BOARD_STORAGE_KEY = "football-analyst.tactics-board.v1"
export const MAX_BOARD_BYTES = 1024 * 1024
export const FORMATIONS = ["4-3-3", "4-2-3-1", "4-4-2", "3-5-2", "3-4-3", "5-4-1"] as const
export type Formation = typeof FORMATIONS[number]
export type BoardTeam = "A" | "B"
export type ObjectType = "player" | "ball" | "pass" | "run" | "zone" | "text"
export type BoardObject = { id: string; type: ObjectType; team: BoardTeam; x_m: number; y_m: number; end_x_m?: number; end_y_m?: number; number?: number; label: string }
export type BoardPhase = { id: string; name: string; notes: string; objects: BoardObject[]; formations: Record<BoardTeam, Formation> }
export type TacticsBoard = { kind: "tactics_board_v1"; title: string; colors: Record<BoardTeam, string>; phases: BoardPhase[] }

export function clampPoint(x_m: number, y_m: number) {
  return { x_m: Math.max(0, Math.min(105, x_m)), y_m: Math.max(0, Math.min(68, y_m)) }
}

export function formationPlayers(team: BoardTeam, formation: Formation, existing: BoardObject[] = []): BoardObject[] {
  const lines = formation.split("-").map(Number)
  const positions = [{ x_m: 6, y_m: 34 }]
  lines.forEach((count, row) => {
    for (let i = 0; i < count; i++) positions.push({ x_m: 18 + row * 30 / (lines.length - 1), y_m: (i + 1) * 68 / (count + 1) })
  })
  return positions.map((point, i) => ({
    id: existing[i]?.id ?? `${team}-player-${i + 1}`, type: "player", team,
    x_m: team === "A" ? point.x_m : 105 - point.x_m,
    y_m: team === "A" ? point.y_m : 68 - point.y_m,
    number: existing[i]?.number ?? i + 1, label: existing[i]?.label ?? (i === 0 ? "GK" : ""),
  }))
}

export function initialBoard(): TacticsBoard {
  return { kind: "tactics_board_v1", title: "Triển khai bóng từ tuyến dưới", colors: { A: "#ec4899", B: "#3b82f6" },
    phases: [{ id: "phase-1", name: "Tổ chức đội hình", notes: "", formations: { A: "4-3-3", B: "4-4-2" },
      objects: [...formationPlayers("A", "4-3-3"), ...formationPlayers("B", "4-4-2"),
        { id: "ball-1", type: "ball", team: "A", x_m: 52.5, y_m: 34, label: "" }] }] }
}

export function applyFormation(phase: BoardPhase, team: BoardTeam, formation: Formation): BoardPhase {
  const existing = phase.objects.filter(object => object.type === "player" && object.team === team)
  const occupied = new Set(phase.objects.filter(object => object.type !== "player" || object.team !== team).map(object => object.id))
  const players = formationPlayers(team, formation, existing).map((object, index) => {
    let id = object.id
    let suffix = 1
    while (occupied.has(id)) id = `${team}-formation-${index}-${suffix++}`
    occupied.add(id)
    return { ...object, id }
  })
  return { ...phase, formations: { ...phase.formations, [team]: formation },
    objects: [...phase.objects.filter(object => object.type !== "player" || object.team !== team), ...players] }
}

export function translateObject(object: BoardObject, dx: number, dy: number): BoardObject {
  const xs = [object.x_m, object.end_x_m ?? object.x_m], ys = [object.y_m, object.end_y_m ?? object.y_m]
  const x = Math.max(-Math.min(...xs), Math.min(105 - Math.max(...xs), dx))
  const y = Math.max(-Math.min(...ys), Math.min(68 - Math.max(...ys), dy))
  return { ...object, x_m: object.x_m + x, y_m: object.y_m + y,
    ...(object.end_x_m !== undefined ? { end_x_m: object.end_x_m + x, end_y_m: object.end_y_m! + y } : {}) }
}

export type BoardHistory = { past: TacticsBoard[]; present: TacticsBoard; future: TacticsBoard[] }
export type BoardAction = { type: "commit"; board: TacticsBoard } | { type: "undo" | "redo" }
export function boardReducer(state: BoardHistory, action: BoardAction): BoardHistory {
  if (action.type === "undo") return state.past.length ? { past: state.past.slice(0, -1), present: state.past[state.past.length - 1], future: [state.present, ...state.future].slice(0, 40) } : state
  if (action.type === "redo") return state.future.length ? { past: [...state.past, state.present].slice(-40), present: state.future[0], future: state.future.slice(1) } : state
  if (action.type !== "commit" || JSON.stringify(action.board) === JSON.stringify(state.present)) return state
  return { past: [...state.past, state.present].slice(-40), present: action.board, future: [] }
}

export function parseTacticsBoard(content: string): TacticsBoard {
  const fail = (): never => { throw new Error("File bảng chiến thuật không hợp lệ hoặc vượt giới hạn.") }
  if (new TextEncoder().encode(content).length > MAX_BOARD_BYTES) fail()
  let raw
  try { raw = JSON.parse(content.replace(/^\uFEFF/, "")) } catch { return fail() }
  const text = (value: unknown, max: number): string => typeof value === "string" && value.length <= max ? value : fail()
  const identifier = (value: unknown): string => typeof value === "string" && /^[a-zA-Z0-9_-]{1,100}$/.test(value) ? value : fail()
  const coordinate = (value: unknown, max: number): number => typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= max ? value : fail()
  if (!raw || raw.kind !== "tactics_board_v1" || !raw.colors || !/^#[a-f0-9]{6}$/i.test(raw.colors.A) || !/^#[a-f0-9]{6}$/i.test(raw.colors.B) || !Array.isArray(raw.phases) || raw.phases.length < 1 || raw.phases.length > 8) fail()
  const phaseIds = new Set<string>()
  const phases = raw.phases.map((phase: BoardPhase): BoardPhase => {
    if (!phase || !Array.isArray(phase.objects) || phase.objects.length > 150 || !phase.formations || !FORMATIONS.includes(phase.formations.A) || !FORMATIONS.includes(phase.formations.B)) fail()
    const id = identifier(phase.id)
    if (phaseIds.has(id)) fail()
    phaseIds.add(id)
    const ids = new Set<string>()
    const objects = phase.objects.map((object): BoardObject => {
      if (!object || !["player", "ball", "pass", "run", "zone", "text"].includes(object.type) || !["A", "B"].includes(object.team)) fail()
      const objectId = identifier(object.id)
      if (ids.has(objectId)) fail()
      ids.add(objectId)
      const base = { id: objectId, type: object.type, team: object.team, x_m: coordinate(object.x_m, 105), y_m: coordinate(object.y_m, 68), label: text(object.label, 60) }
      if (object.type === "player") {
        if (!Number.isInteger(object.number) || object.number! < 1 || object.number! > 99) fail()
        return { ...base, number: object.number }
      }
      if (["pass", "run", "zone"].includes(object.type)) return { ...base, end_x_m: coordinate(object.end_x_m, 105), end_y_m: coordinate(object.end_y_m, 68) }
      return base
    })
    if (objects.filter(object => object.type === "ball").length > 1) fail()
    return { id, name: text(phase.name, 80), notes: text(phase.notes, 4000), formations: { A: phase.formations.A, B: phase.formations.B }, objects }
  })
  return { kind: "tactics_board_v1", title: text(raw.title, 100), colors: { A: raw.colors.A, B: raw.colors.B }, phases }
}

export function storeTacticsBoard(storage: Pick<Storage, "setItem">, board: TacticsBoard) {
  const content = JSON.stringify(board)
  parseTacticsBoard(content)
  storage.setItem(BOARD_STORAGE_KEY, content)
}
