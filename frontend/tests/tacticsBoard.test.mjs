import test from "node:test"
import assert from "node:assert/strict"
import { applyFormation, BOARD_STORAGE_KEY, boardReducer, clampPoint, FORMATIONS, formationPlayers, initialBoard, MAX_BOARD_BYTES, parseTacticsBoard, storeTacticsBoard, translateObject } from "../src/lib/tacticsBoard.ts"

test("every formation has eleven unique players, valid metre coordinates and mirrored teams", () => {
  for (const formation of FORMATIONS) {
    const a = formationPlayers("A", formation), b = formationPlayers("B", formation)
    assert.equal(a.length, 11); assert.equal(new Set(a.map(player => player.id)).size, 11)
    for (let i = 0; i < 11; i++) {
      assert.equal(a[i].x_m + b[i].x_m, 105)
      assert.equal(a[i].y_m + b[i].y_m, 68)
      assert.ok(a[i].x_m >= 0 && a[i].x_m <= 105 && a[i].y_m >= 0 && a[i].y_m <= 68)
    }
  }
})

test("changing formation affects selected team only and preserves player identity and custom labels", () => {
  const phase = initialBoard().phases[0]
  phase.objects[1].label = "Tuấn"; phase.objects[1].number = 27
  const before = structuredClone(phase.objects.filter(object => object.team === "B" || object.type !== "player"))
  const next = applyFormation(phase, "A", "4-2-3-1")
  assert.deepEqual(next.objects.filter(object => object.team === "B" || object.type !== "player"), before)
  const player = next.objects.find(object => object.id === phase.objects[1].id)
  assert.equal(player.label, "Tuấn"); assert.equal(player.number, 27)
  assert.equal(next.formations.A, "4-2-3-1"); assert.equal(phase.formations.A, "4-3-3")
})

test("formation IDs cannot collide with imported annotations or opposite team", () => {
  const phase = initialBoard().phases[0]
  phase.objects = [{ id: "A-player-1", type: "text", team: "B", x_m: 5, y_m: 5, label: "Vùng" }]
  const next = applyFormation(phase, "A", "4-3-3")
  assert.equal(new Set(next.objects.map(object => object.id)).size, next.objects.length)
})

test("drag bounds preserve complete arrows rather than clipping one endpoint or changing length", () => {
  const line = { id: "p", type: "pass", team: "A", x_m: 90, y_m: 40, end_x_m: 100, end_y_m: 60, label: "" }
  const moved = translateObject(line, 30, 20)
  assert.equal(moved.end_x_m, 105); assert.equal(moved.x_m, 95)
  assert.equal(moved.end_y_m, 68); assert.equal(moved.y_m, 48)
  assert.equal(moved.end_x_m - moved.x_m, 10); assert.equal(moved.end_y_m - moved.y_m, 20)
  assert.deepEqual(clampPoint(-100, 100), { x_m: 0, y_m: 68 })
})

test("undo and redo restore exact board, discard future after edits and bound history", () => {
  const board = initialBoard()
  let state = { past: [], present: board, future: [] }
  assert.equal(boardReducer(state, { type: "undo" }), state)
  assert.equal(boardReducer(state, { type: "commit", board: structuredClone(board) }), state)
  const changed = { ...board, title: "Pressing" }
  state = boardReducer(state, { type: "commit", board: changed })
  state = boardReducer(state, { type: "undo" }); assert.deepEqual(state.present, board)
  state = boardReducer(state, { type: "redo" }); assert.deepEqual(state.present, changed)
  state = boardReducer(state, { type: "undo" })
  state = boardReducer(state, { type: "commit", board: { ...board, title: "New" } })
  assert.equal(state.future.length, 0)
  for (let i = 0; i < 50; i++) state = boardReducer(state, { type: "commit", board: { ...board, title: String(i) } })
  assert.equal(state.past.length, 40)
})

test("JSON round-trip retains both teams, notes, phases and drawing coordinates independently", () => {
  const board = initialBoard()
  board.phases[0].notes = "Mở rộng biên và tạo tam giác"
  board.phases[0].objects.push({ id: "pass-1", type: "pass", team: "A", x_m: 20, y_m: 25, end_x_m: 40, end_y_m: 45, label: "" })
  board.phases.push({ ...structuredClone(board.phases[0]), id: "second", name: "Tiến bóng" })
  const loaded = parseTacticsBoard("\uFEFF" + JSON.stringify(board))
  assert.deepEqual(loaded, board)
  loaded.phases[1].objects[0].x_m = 30
  assert.equal(loaded.phases[0].objects[0].x_m, 6)
})

test("rejects unsafe or corrupt board files and never treats tracking JSON as a board", () => {
  const mutations = [board => board.kind = "TrackingRow", board => board.colors.A = "url(http://bad)",
    board => board.phases = [], board => board.phases[0].objects[0].x_m = 106,
    board => board.phases[0].objects[0].y_m = -1, board => board.phases[0].objects[0].number = 1.5,
    board => board.phases[0].objects[0].team = "referee", board => board.phases[0].formations.A = "10-0-0",
    board => board.phases[0].objects[0].type = "unknown", board => board.title = "a".repeat(101),
    board => board.phases[0].objects[1].id = board.phases[0].objects[0].id,
    board => board.phases[0].objects.push({ ...board.phases[0].objects.at(-1), id: "another-ball" }),
    board => board.phases.push(structuredClone(board.phases[0])),
    board => board.phases[0].objects.push({ id: "bad-arrow", type: "pass", team: "A", x_m: 1, y_m: 1, label: "" })]
  for (const mutate of mutations) { const board = initialBoard(); mutate(board); assert.throws(() => parseTacticsBoard(JSON.stringify(board))) }
  for (const text of ["null", "[]", "not json", " ".repeat(MAX_BOARD_BYTES + 1)]) assert.throws(() => parseTacticsBoard(text))
})

test("phase and object limits still allow an intentionally empty training scene", () => {
  const board = initialBoard(); board.phases[0].objects = []
  assert.equal(parseTacticsBoard(JSON.stringify(board)).phases[0].objects.length, 0)
  board.phases = Array.from({ length: 9 }, (_, i) => ({ ...board.phases[0], id: `phase-${i}` }))
  assert.throws(() => parseTacticsBoard(JSON.stringify(board)))
  board.phases = [initialBoard().phases[0]]
  board.phases[0].objects = Array.from({ length: 151 }, (_, i) => ({ ...board.phases[0].objects[0], id: `obj-${i}` }))
  assert.throws(() => parseTacticsBoard(JSON.stringify(board)))
})

test("storage validates before replacing a saved board and reports quota failure", () => {
  const data = new Map(), storage = { setItem: (key, value) => data.set(key, value) }
  const board = initialBoard()
  storeTacticsBoard(storage, board)
  const before = data.get(BOARD_STORAGE_KEY)
  assert.deepEqual(parseTacticsBoard(before), board)
  assert.throws(() => storeTacticsBoard(storage, { ...board, phases: [] }))
  assert.equal(data.get(BOARD_STORAGE_KEY), before)
  assert.throws(() => storeTacticsBoard({ setItem: () => { throw new Error("QuotaExceededError") } }, board), /Quota/)
})
