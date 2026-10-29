import test from "node:test"
import assert from "node:assert/strict"
import { parseTracking, frameAt, trackingRanges, compatibilityError } from "../src/lib/videoTracking.ts"

const row = (frame, track_id = 1) => ({ frame, time_s: frame / 60, track_id, team: "A", x_m: 20, y_m: 30 })

test("accepts JSONL/BOM/CRLF and arrays, groups people and sorts frames", () => {
  const rows = [row(60), row(0, 2), row(0)]
  const a = parseTracking("\uFEFF" + rows.map(r => JSON.stringify(r)).join("\r\n"))
  const b = parseTracking(JSON.stringify(rows))
  assert.deepEqual(a, b)
  assert.equal(a.frames.length, 2)
  assert.equal(a.frames[0].rows.length, 2)
  assert.equal(a.frameDuration, 1 / 60)
})

test("rejects corruption, duplicate IDs, out-of-pitch, wrong time and missing fields", () => {
  for (const invalid of ["", "{}", "[]", "not json", JSON.stringify([{ ...row(0), x_m: 106 }]),
    JSON.stringify([{ ...row(0), y_m: -1 }]), JSON.stringify([{ ...row(0), team: "home" }]),
    JSON.stringify([{ ...row(0), team: ["A"] }]),
    JSON.stringify([{ ...row(0), frame: .5 }]), JSON.stringify([{ ...row(0), track_id: -1 }]),
    JSON.stringify([{ ...row(0), time_s: "0" }]), JSON.stringify([row(0), row(0)]),
    JSON.stringify([row(0), { ...row(1), time_s: 0 }]),
    JSON.stringify([row(0), { ...row(0, 2), time_s: .1 }])]) {
    assert.throws(() => parseTracking(invalid))
  }
})

test("shows only the active source frame, applies offset, clears gaps and stale IDs", () => {
  const timeline = parseTracking(JSON.stringify([row(0), row(1, 2), row(600, 3)]))
  assert.equal(frameAt(timeline, 10, 10).rows[0].track_id, 1)
  assert.equal(frameAt(timeline, 10 + 1 / 60, 10).rows[0].track_id, 2)
  assert.equal(frameAt(timeline, 10.2, 10), null)
  assert.equal(frameAt(timeline, 9.9, 10), null)
  assert.equal(frameAt(timeline, 20, 10).rows[0].track_id, 3)
  assert.equal(frameAt(timeline, 20.1, 10), null)
  assert.equal(frameAt(timeline, 11, NaN), null)
  assert.equal(trackingRanges(timeline).length, 2)
})

test("seeking backwards is independent of playback history and checks clip mismatch", () => {
  const timeline = parseTracking(JSON.stringify([row(0), row(1), row(600)]))
  frameAt(timeline, 10, 0)
  assert.equal(frameAt(timeline, 0, 0).frame, 0)
  assert.equal(compatibilityError(timeline, 11, 0), null)
  assert.match(compatibilityError(timeline, 5, 0), /ngoài thời lượng/)
  assert.match(compatibilityError(timeline, 11, 20), /không giao/)
  assert.match(compatibilityError(timeline, 11, NaN), /hợp lệ/)
})

test("rounded media-clock seeks show the first frame without retaining coordinates across a gap", () => {
  const timeline = parseTracking(JSON.stringify([904, 905, 1199, 1204].map(frame => ({ ...row(frame), time_s: frame / 30 }))))
  assert.equal(frameAt(timeline, Math.fround(904 / 30), 0)?.frame, 904)
  assert.equal(frameAt(timeline, Math.fround(905 / 30), 0)?.frame, 905)
  assert.equal(frameAt(timeline, Math.fround(1204 / 30), 0)?.frame, 1204)
  assert.equal(frameAt(timeline, 40, 0), null)
  assert.equal(frameAt(timeline, Math.fround(1203 / 30), 0), null)
  assert.equal(frameAt(timeline, 904 / 30 - .001, 0), null)
})
