import { log, logError } from "./logger"

export async function measureUploadSpeed(durationMs = 3000, chunkSize = 64 * 1024): Promise<number> {
  // Upload random data chunks to local API that discards the body
  const endpoint = "/api/upload-speed"
  const start = performance.now()
  let bytesSent = 0
  let iterations = 0

  // Pre-generate a chunk (zero-filled). Avoid getRandomValues 64KB cap issues.
  const MAX_CHUNK = 64 * 1024
  const size = Math.min(chunkSize, MAX_CHUNK)
  const chunk = new Uint8Array(size)

  try {
    log("[NetSpeed] Starting upload speed test", { durationMs, chunkSize: size })
    while (performance.now() - start < durationMs) {
      iterations += 1
      let res: Response | null = null
      try {
        res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/octet-stream" },
        body: chunk,
        keepalive: true,
        })
      } catch (e) {
        logError("[NetSpeed] Fetch failed during speed test", { iteration: iterations, error: e instanceof Error ? e.message : String(e) })
        break
      }
      if (!res.ok) {
        logError("[NetSpeed] Non-OK response during speed test", { status: res.status })
        break
      }
      bytesSent += size
      // Yield to allow UI to remain responsive
      await new Promise((r) => setTimeout(r, 0))
    }
  } catch {
    // Ignore errors; return whatever we measured
  }

  const elapsed = Math.max(1, performance.now() - start) / 1000
  const bps = bytesSent / elapsed
  log("[NetSpeed] Speed test finished", { bytesSent, seconds: elapsed, iterations, bps })
  return bps
}

export function saveUploadSpeed(bps: number) {
  try {
    if (bps > 0) {
      localStorage.setItem("upload_speed_bps", String(Math.floor(bps)))
      localStorage.setItem("upload_speed_ts", String(Date.now()))
      log("[NetSpeed] Saved upload speed", { bps: Math.floor(bps) })
    }
  } catch {}
}

export function getSavedUploadSpeed(maxAgeMs = 5 * 60 * 1000): number | null {
  try {
    const tsRaw = localStorage.getItem("upload_speed_ts")
    const bpsRaw = localStorage.getItem("upload_speed_bps")
    if (!tsRaw || !bpsRaw) return null
    const ts = parseInt(tsRaw)
    const bps = parseInt(bpsRaw)
    if (!Number.isFinite(ts) || !Number.isFinite(bps)) return null
    if (Date.now() - ts > maxAgeMs) return null
    return bps
  } catch {
    return null
  }
}
