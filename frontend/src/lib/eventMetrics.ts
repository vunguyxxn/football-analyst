import type { MetricItem } from "./types.ts"

export function formatEventMetric(metric: MetricItem): string {
  if (typeof metric.value !== "number" || !Number.isFinite(metric.value)) return "Chưa đủ dữ liệu"
  const number = new Intl.NumberFormat("vi-VN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  if (metric.unit === "tỷ lệ") return `${number.format(metric.value * 100)}%`
  return number.format(metric.value)
}
