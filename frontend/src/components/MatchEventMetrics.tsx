import { useQuery } from "@tanstack/react-query"
import { fetchEventMetrics, fetchMetricDefinitions } from "@/lib/api"
import { formatEventMetric } from "@/lib/eventMetrics"
import "./matchEventMetrics.css"

export default function MatchEventMetrics({ matchId, team, ready }: { matchId: number; team: string; ready: boolean }) {
  const metrics = useQuery({
    queryKey: ["event-metrics", matchId, team],
    queryFn: () => fetchEventMetrics(matchId, team),
    // The pass-network request warms the same CSV cache. Avoid simultaneous
    // first-time downloads/writes when a match has not been cached yet.
    enabled: ready,
  })
  const definitions = useQuery({
    queryKey: ["metric-definitions"],
    queryFn: fetchMetricDefinitions,
    staleTime: 60 * 60 * 1000,
  })

  return (
    <section className="event-metrics card-surface" aria-label={`Chỉ số sự kiện của ${team}`}>
      <div className="panel-heading">
        <div>
          <h3>Chỉ số sự kiện · {team}</h3>
          <p>Toàn trận và hiệp phụ · loại luân lưu · nguồn StatsBomb</p>
        </div>
      </div>
      <p className="event-metrics-context">
        Các chỉ số dùng toàn trận; sơ đồ chuyền giới hạn trước lần thay người đầu tiên.
        PPDA và field tilt cần được đọc cùng diễn biến, tỷ số và phạm vi dữ liệu.
      </p>
      {metrics.isPending && <p role="status">Đang tính chỉ số sự kiện…</p>}
      {metrics.isError && <p role="alert">Không thể tải chỉ số. {metrics.error.message}</p>}
      {definitions.isError && <p role="alert">Chưa tải được phần giải thích phương pháp. {definitions.error.message}</p>}
      <div className="event-metrics-grid">
        {metrics.data?.metrics.map((metric) => {
          const definition = definitions.data?.find((card) => card.key === metric.key)
          return (
            <article className="event-metric" key={metric.key}>
              <h4>{metric.label}</h4>
              <strong className="event-metric-value">{formatEventMetric(metric)}</strong>
              {typeof metric.value === "number" && metric.unit && metric.unit !== "tỷ lệ" && <span>{metric.unit}</span>}
              {typeof metric.value === "string" && <p className="event-metric-unavailable">{metric.value}</p>}
              {definition ? (
                <details>
                  <summary>Cách tính và nguồn</summary>
                  <p>{definition.formula}</p>
                  <p>{definition.interpretation}</p>
                  <ul>{definition.caveats.map((caveat) => <li key={caveat}>{caveat}</li>)}</ul>
                  <a href={definition.source_url} target="_blank" rel="noreferrer">Nguồn phương pháp</a>
                  {" · "}
                  <a href={definition.reference_url} target="_blank" rel="noreferrer">Định nghĩa tham khảo</a>
                  <p className="event-metric-variant">{definition.key} · phiên bản {definition.version}</p>
                </details>
              ) : definitions.isPending ? <p>Đang tải cách tính…</p> : null}
            </article>
          )
        })}
      </div>
    </section>
  )
}
