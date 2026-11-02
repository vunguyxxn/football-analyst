import test from "node:test"
import assert from "node:assert/strict"
import { formatEventMetric } from "../src/lib/eventMetrics.ts"

test("formats ratios, zero totals and explicit missing evidence without coercion", () => {
  assert.equal(formatEventMetric({ value: .6186, unit: "tỷ lệ" }), "61.86%")
  assert.equal(formatEventMetric({ value: 7.4222, unit: "chuyền/hành động" }), "7.42")
  assert.equal(formatEventMetric({ value: 0, unit: "bàn kỳ vọng" }), "0.00")
  for (const value of ["Thiếu trường dữ liệu: pass_outcome", "0", NaN, Infinity]) {
    assert.equal(formatEventMetric({ value, unit: "tỷ lệ" }), "Chưa đủ dữ liệu")
  }
})
