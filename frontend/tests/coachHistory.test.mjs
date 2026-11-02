import test from "node:test"
import assert from "node:assert/strict"
import { parseCoachReport } from "../src/lib/coachReport.ts"
import { COACH_HISTORY_KEY, MAX_HISTORY_BYTES, coachOpenedTime, coachProvenance, coachReportFingerprint, readCoachHistory, restoreCoachHistory, saveCoachHistory } from "../src/lib/coachHistory.ts"

// A valid no-shot report exercises persistence without requiring local demo
// assets. Numerical/SHAP and shot-link checks have their own parser tests.
const source = {
  kind: "shot_advisor_v1", source: "statsbomb", timing: "post_match", match_id: 10,
  model_audit: { method: "TreeExplainer/tree_path_dependent", units: "log_odds", trees_explained: 2, best_iteration: 1, model_sha256: "a".repeat(64) },
  protocol: { minimum_team_shots: 5, minimum_subset_shots: 3, low_xg_threshold: .08, high_xg_threshold: .2, low_xg_fraction: .5, high_xg_fraction: .25, pressure_fraction: .4 },
  limitations: ["Chưa đủ cú sút"], shots: [], provenance: { model_dataset_split: "val" },
  teams: [{ team_id: 1, team: "Đội A", eligible_shots: 0, xg_total: 0, mean_xg: null, status: "insufficient_data", recommendations: [] }],
}
const report = (note = "") => parseCoachReport(JSON.stringify({ ...source, limitations: [...source.limitations, ...(note ? [note] : [])] }))
const time = minute => `2026-11-02T07:${String(minute).padStart(2, "0")}:00.000Z`
function storage() {
  const data = new Map()
  return { getItem: key => data.get(key) ?? null, setItem: (key, value) => data.set(key, value) }
}

test("history restores full verified report after reload and preserves source/provenance", async () => {
  const store = storage(), parsed = report()
  const [entry] = await saveCoachHistory(store, parsed, "Báo cáo Việt Nam.json", time(1))
  assert.equal(entry.matchId, parsed.matchId)
  assert.match(entry.id, /^[a-f0-9]{64}$/)
  assert.deepEqual((await restoreCoachHistory(readCoachHistory(store)[0])).original, parsed.original)
  assert.equal(entry.openedAt, time(1))
})

test("same content deduplicates filenames while changed version of same match stays distinct", async () => {
  const store = storage(), parsed = report()
  await saveCoachHistory(store, parsed, "one.json", time(1))
  let entries = await saveCoachHistory(store, parsed, "renamed.json", time(2))
  assert.equal(entries.length, 1); assert.equal(entries[0].name, "renamed.json")
  entries = await saveCoachHistory(store, report("another snapshot"), "one.json", time(3))
  assert.equal(entries.length, 2); assert.notEqual(entries[0].id, entries[1].id)
  assert.equal(entries[0].matchId, entries[1].matchId)
})

test("keeps five most recent versions and out-of-order saves cannot roll back last-opened time", async () => {
  const store = storage()
  for (let i = 1; i <= 6; i++) await saveCoachHistory(store, report(`version ${i}`), `v${i}`, time(i))
  let entries = readCoachHistory(store)
  assert.deepEqual(entries.map(item => item.name), ["v6", "v5", "v4", "v3", "v2"])
  entries = await saveCoachHistory(store, report("version 6"), "old request", time(0))
  assert.equal(entries[0].name, "v6"); assert.equal(entries[0].openedAt, time(6))
})

test("tampered content, metadata and internally inconsistent report cannot reopen", async () => {
  const [entry] = await saveCoachHistory(storage(), report(), "report", time(1))
  await assert.rejects(restoreCoachHistory({ ...entry, content: entry.content + " " }), /thay đổi/)
  await assert.rejects(restoreCoachHistory({ ...entry, matchId: entry.matchId + 1 }), /không khớp/)
  const bad = JSON.parse(entry.content); bad.teams[0].xg_total = 100
  const content = JSON.stringify(bad)
  await assert.rejects(restoreCoachHistory({ ...entry, content, id: await coachReportFingerprint(content) }), /không khớp/)
})

test("corrupt archive is reported without silently overwriting old data", async () => {
  const store = storage()
  for (const raw of ["not JSON", "null", JSON.stringify({ version: 99, entries: [] }), JSON.stringify({ version: 1, entries: [{}] })]) {
    store.setItem(COACH_HISTORY_KEY, raw)
    assert.throws(() => readCoachHistory(store))
    await assert.rejects(saveCoachHistory(store, report(), "report", time(1)))
    assert.equal(store.getItem(COACH_HISTORY_KEY), raw)
  }
})

test("oversized reports and storage quota failure preserve previously stored report", async () => {
  const store = storage()
  await saveCoachHistory(store, report(), "previous", time(1))
  const before = store.getItem(COACH_HISTORY_KEY)
  await assert.rejects(saveCoachHistory(store, report("a".repeat(MAX_HISTORY_BYTES)), "large", time(2)), /quá lớn/)
  assert.equal(store.getItem(COACH_HISTORY_KEY), before)
  const blocked = { getItem: store.getItem, setItem: () => { throw new Error("QuotaExceededError") } }
  await assert.rejects(saveCoachHistory(blocked, report("next"), "next", time(3)), /Quota/)
  assert.equal(store.getItem(COACH_HISTORY_KEY), before)
})

test("storage budget evicts oldest snapshots before reaching five entries", async () => {
  const store = storage()
  for (let i = 1; i <= 3; i++) await saveCoachHistory(store, report(`${i}${"a".repeat(400_000)}`), `v${i}`, time(i))
  assert.deepEqual(readCoachHistory(store).map(item => item.name), ["v3", "v2"])
  assert.ok(store.getItem(COACH_HISTORY_KEY).length * 2 <= MAX_HISTORY_BYTES)
})

test("missing creation date stays unknown and opening time never becomes source freshness", () => {
  const parsed = report()
  assert.equal(coachProvenance(parsed).generatedAt, null)
  const date = "2026-10-01T01:00:00Z"
  assert.equal(coachProvenance({ ...parsed, original: { ...parsed.original, generated_at: date } }).generatedAt, date)
  assert.equal(coachProvenance({ ...parsed, original: { ...parsed.original, generated_at: "yesterday" } }).generatedAt, null)
  assert.equal(coachProvenance({ ...parsed, original: { ...parsed.original, provenance: { source_revision: "invalid", events_sha256: 123 } } }).eventsHash, null)
  assert.match(coachOpenedTime("2026-11-02T07:00:00Z"), /14:00:00/)
})
