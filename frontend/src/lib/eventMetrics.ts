import type { MetricItem } from "./types.ts"

export function formatEventMetric(metric: MetricItem): string {
  if (typeof metric.value !== "number" || !Number.isFinite(metric.value)) return "Chưa đủ dữ liệu"
  if (metric.unit === "tỷ lệ") return `${(metric.value * 100).toFixed(2)}%`
  return metric.value.toFixed(2)
}
