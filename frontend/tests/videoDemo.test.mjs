import test from "node:test"
import assert from "node:assert/strict"
import { fetchCompletedDemo } from "../src/lib/useVideoJob.ts"

test("processed demo requires completed job and the exact source-video hash", async () => {
  const original = globalThis.fetch
  const hash = "a".repeat(64)
  const signal = new AbortController().signal
  let status = "completed", actualHash = hash
  globalThis.fetch = async (url, options) => {
    assert.equal(url, "/api/video-jobs/demo")
    assert.equal(options.signal, signal)
    return new Response(JSON.stringify({ id: "demo", status, result: { source_sha256: actualHash } }), { status: 200 })
  }
  try {
    assert.equal((await fetchCompletedDemo("demo", hash, signal)).id, "demo")
    actualHash = "b".repeat(64)
    await assert.rejects(() => fetchCompletedDemo("demo", hash, signal), /không khớp/)
    actualHash = hash
    status = "running"
    await assert.rejects(() => fetchCompletedDemo("demo", hash, signal), /chưa sẵn sàng/)
  } finally { globalThis.fetch = original }
})
