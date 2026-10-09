import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { AnimatePresence, motion } from "framer-motion"
import { AlertCircle, ArrowDownRight, ArrowUpRight, LoaderCircle } from "lucide-react"
import Pitch from "@/components/Pitch"
import { SelectField, type SelectOption } from "@/components/ui/select"
import {
  fetchCompetitions,
  fetchMatches,
  fetchPassNetwork,
} from "@/lib/api"
import type { Competition, Match, PassNetworkNode } from "@/lib/types"
import { toSvg } from "@/lib/pitchCoordinates"

const EMPTY_COMPETITIONS: Competition[] = []
const EMPTY_MATCHES: Match[] = []

function LoadingState({ label }: { label: string }) {
  return (
    <div aria-label={label} className="analysis-loading" role="status">
      <div className="skeleton skeleton-line skeleton-short" />
      <div className="skeleton skeleton-pitch" />
      <div className="skeleton skeleton-line" />
    </div>
  )
}

function ErrorNotice({ message }: { message: string }) {
  return (
    <div className="error-notice" role="alert">
      <AlertCircle aria-hidden="true" size={18} />
      <span>{message}</span>
    </div>
  )
}

function getSurname(fullName: string): string {
  const words = fullName.trim().split(/\s+/)
  return words[words.length - 1] ?? fullName
}

function formatMatch(match: Match): string {
  const score =
    match.home_score !== null && match.away_score !== null
      ? ` · ${match.home_score}–${match.away_score}`
      : ""
  return `${match.home_team} – ${match.away_team}${score}`
}

function NetworkPitch({
  nodes,
  edges,
}: {
  nodes: PassNetworkNode[]
  edges: { source: string; target: string; count: number }[]
}) {
  const nodesByPlayer = useMemo(
    () => new Map(nodes.map((node) => [node.player, node])),
    [nodes],
  )
  const labeledPlayers = useMemo(
    () =>
      new Set(
        [...nodes]
          .sort((left, right) => right.pass_count - left.pass_count)
          .slice(0, 6)
          .map((node) => node.player),
      ),
    [nodes],
  )

  return (
    <div className="pitch-frame">
      <Pitch className="match-pitch">
        {edges.map((edge) => {
          const source = nodesByPlayer.get(edge.source)
          const target = nodesByPlayer.get(edge.target)
          if (!source || !target) return null
          const start = toSvg(source.avg_x_m, source.avg_y_m)
          const end = toSvg(target.avg_x_m, target.avg_y_m)
          const thickness = Math.min(0.7, 0.16 + edge.count * 0.025)
          const opacity = Math.min(0.74, 0.22 + edge.count * 0.024)
          return (
            <line
              key={`${edge.source}-${edge.target}`}
              opacity={opacity}
              stroke="#86efac"
              strokeWidth={thickness}
              x1={start.x}
              x2={end.x}
              y1={start.y}
              y2={end.y}
            />
          )
        })}
        {nodes.map((node) => {
          const point = toSvg(node.avg_x_m, node.avg_y_m)
          const radius = Math.min(1.9, 0.95 + node.pass_count * 0.035)
          return (
            <g className="pitch-player-group" key={node.player}>
              <circle
                cx={point.x}
                cy={point.y}
                fill="#22c55e"
                fillOpacity="0.96"
                r={radius}
                stroke="#e5e7eb"
                strokeOpacity="0.8"
                strokeWidth="0.2"
              >
                <title>
                  {`${node.player} · ${node.pass_count} chuyền · ${node.touches} lần chạm`}
                </title>
              </circle>
              <text
                className={`pitch-player-label${labeledPlayers.has(node.player) ? " is-priority" : ""}`}
                dominantBaseline="middle"
                textAnchor="middle"
                x={point.x}
                y={point.y + radius + 1.5}
              >
                {node.short_name}
              </text>
            </g>
          )
        })}
      </Pitch>
      <div aria-hidden="true" className="pitch-direction">
        <span>TẤN CÔNG</span>
        <ArrowUpRight size={15} />
      </div>
    </div>
  )
}

function StatCard({
  label,
  value,
  footnote,
  icon,
}: {
  label: string
  value: string | number
  footnote: string
  icon: "up" | "down"
}) {
  const TrendIcon = icon === "up" ? ArrowUpRight : ArrowDownRight
  return (
    <div className="stat-card card-surface">
      <span className="stat-label">{label}</span>
      <strong className="stat-value">{value}</strong>
      <span className="stat-footnote">
        <TrendIcon aria-hidden="true" size={14} />
        {footnote}
      </span>
    </div>
  )
}

export default function MatchAnalysis() {
  const [competitionId, setCompetitionId] = useState("43")
  const [seasonId, setSeasonId] = useState("3")
  const [matchId, setMatchId] = useState("8650")
  const [team, setTeam] = useState("Brazil")

  const competitionsQuery = useQuery({
    queryKey: ["competitions"],
    queryFn: fetchCompetitions,
    staleTime: 60 * 60 * 1000,
  })
  const competitions = competitionsQuery.data ?? EMPTY_COMPETITIONS
  const competitionRows = useMemo(() => {
    const seen = new Set<number>()
    return competitions.filter((item) => {
      if (seen.has(item.competition_id)) return false
      seen.add(item.competition_id)
      return true
    })
  }, [competitions])
  const selectedCompetitionId = competitionRows.some(
    (competition) => String(competition.competition_id) === competitionId,
  )
    ? competitionId
    : String(competitionRows[0]?.competition_id ?? "")
  const seasons = competitions.filter(
    (item) => String(item.competition_id) === selectedCompetitionId,
  )
  const selectedSeason =
    seasons.find((season) => String(season.season_id) === seasonId) ??
    seasons.find(
      (season) =>
        season.competition_id === 43 && season.season_id === 3,
    ) ??
    seasons[0]
  const selectedSeasonId = selectedSeason ? String(selectedSeason.season_id) : ""
  const matchesQuery = useQuery({
    queryKey: ["matches", selectedCompetitionId, selectedSeasonId],
    queryFn: () =>
      fetchMatches(Number(selectedCompetitionId), Number(selectedSeasonId)),
    enabled: Boolean(selectedCompetitionId && selectedSeasonId),
    staleTime: 60 * 60 * 1000,
  })
  const matches = matchesQuery.data ?? EMPTY_MATCHES
  const selectedMatch =
    matches.find((match) => String(match.match_id) === matchId) ??
    matches.find((match) => match.match_id === 8650) ??
    matches[0]
  const selectedMatchId = selectedMatch ? String(selectedMatch.match_id) : ""
  const teamOptions = selectedMatch
    ? [selectedMatch.home_team, selectedMatch.away_team]
    : []
  const selectedTeam = teamOptions.includes(team)
    ? team
    : teamOptions.includes("Brazil")
      ? "Brazil"
      : (teamOptions[0] ?? "")
  const networkQuery = useQuery({
    queryKey: ["pass-network", selectedMatchId, selectedTeam],
    queryFn: () => fetchPassNetwork(Number(selectedMatchId), selectedTeam),
    enabled: Boolean(selectedMatchId && selectedTeam),
  })
  const network = networkQuery.data

  const competitionOptions: SelectOption[] = competitionRows.map((item) => ({
    value: String(item.competition_id),
    label: item.competition_name,
  }))
  const seasonOptions: SelectOption[] = seasons.map((item) => ({
    value: String(item.season_id),
    label: item.season_name,
  }))
  const matchOptions: SelectOption[] = matches.map((item) => ({
    value: String(item.match_id),
    label: formatMatch(item),
  }))
  const teamSelectOptions: SelectOption[] = teamOptions.map((name) => ({
    value: name,
    label: name,
  }))
  const strongestEdge = network?.edges.reduce(
    (strongest, edge) => (edge.count > strongest.count ? edge : strongest),
    network.edges[0] ?? { source: "—", target: "", count: 0 },
  )
  const topPlayers = [...(network?.nodes ?? [])]
    .sort((left, right) => right.pass_count - left.pass_count)
    .slice(0, 8)

  return (
    <motion.div
      animate={{ opacity: 1, y: 0 }}
      className="match-page"
      initial={{ opacity: 0, y: 8 }}
      transition={{ duration: 0.2 }}
    >
      <section className="match-intro">
        <div>
          <span className="eyebrow">STATSBOMB OPEN DATA</span>
          <h2>Phân tích trận</h2>
          <p>Khám phá cách đội bóng kết nối qua từng đường chuyền.</p>
        </div>
        <div className="live-badge">
          <span />
          DỮ LIỆU THẬT
        </div>
      </section>

      <section aria-label="Chọn trận đấu" className="filter-panel card-surface">
        <SelectField
          disabled={competitionsQuery.isPending || competitionOptions.length === 0}
          label="Giải đấu"
          onValueChange={(value) => {
            if (value) {
              setCompetitionId(value)
              setSeasonId("")
              setMatchId("")
            }
          }}
          options={competitionOptions}
          placeholder={
            competitionsQuery.isPending ? "Đang tải giải đấu..." : "Chọn giải đấu"
          }
          value={selectedCompetitionId || null}
        />
        <SelectField
          disabled={!competitionId || seasonOptions.length === 0}
          label="Mùa giải"
          onValueChange={(value) => {
            if (value) {
              setSeasonId(value)
              setMatchId("")
            }
          }}
          options={seasonOptions}
          placeholder="Chọn mùa giải"
          value={selectedSeasonId || null}
        />
        <SelectField
          disabled={matchesQuery.isPending || matches.length === 0}
          label="Trận đấu"
          onValueChange={(value) => {
            if (value) setMatchId(value)
          }}
          options={matchOptions}
          placeholder={
            matchesQuery.isPending ? "Đang tải trận..." : "Chọn trận đấu"
          }
          value={selectedMatchId || null}
        />
        <SelectField
          disabled={!selectedMatch}
          label="Đội"
          onValueChange={(value) => {
            if (value) setTeam(value)
          }}
          options={teamSelectOptions}
          placeholder="Chọn đội"
          value={selectedTeam || null}
        />
      </section>

      {competitionsQuery.isError && (
        <ErrorNotice
          message={`Không thể tải danh sách giải đấu. ${competitionsQuery.error.message}`}
        />
      )}
      {matchesQuery.isError && (
        <ErrorNotice
          message={`Không thể tải danh sách trận đấu. ${matchesQuery.error.message}`}
        />
      )}
      {networkQuery.isError && (
        <ErrorNotice
          message={`Không thể tải pass network. ${networkQuery.error.message}`}
        />
      )}

      <div className="match-summary card-surface">
        <div>
          <span className="summary-kicker">
            {selectedMatch?.competition_stage ?? "TRẬN ĐẤU"}
          </span>
          <h3>
            {selectedMatch
              ? `${selectedMatch.home_team}  —  ${selectedMatch.away_team}`
              : "Đang tải thông tin trận"}
          </h3>
          <span className="summary-date">
            {selectedMatch?.match_date ?? "World Cup · 2018"}
          </span>
        </div>
        <div className="scoreline">
          <span>{selectedMatch?.home_score ?? "—"}</span>
          <i>:</i>
          <span>{selectedMatch?.away_score ?? "—"}</span>
        </div>
      </div>

      {networkQuery.isPending && selectedMatch ? (
        <LoadingState label="Đang tải sơ đồ chuyền bóng" />
      ) : network ? (
        <div className="analysis-grid">
          <section className="pitch-card card-surface">
            <div className="panel-heading">
              <div>
                <h3>Sơ đồ chuyền bóng</h3>
                <p>
                  {team} <span>·</span> {network.nodes.length} cầu thủ tham gia
                </p>
              </div>
              <div aria-label="Chú giải" className="legend">
                <span className="legend-line" />
                <span>Đường chuyền</span>
                <span className="legend-dot" />
                <span>Cầu thủ</span>
              </div>
            </div>
            {network.nodes.length ? (
              <NetworkPitch nodes={network.nodes} edges={network.edges} />
            ) : (
              <div className="empty-network">
                Chưa có dữ liệu chuyền bóng cho đội này trong trận đấu.
              </div>
            )}
            <div className="pitch-footnote">
              <span>TRỤC TỌA ĐỘ SÂN CHUẨN</span>
              <span>105 × 68 M</span>
            </div>
          </section>

          <aside className="analysis-sidebar">
            <section className="stats-grid" aria-label="Chỉ số chuyền bóng">
              <StatCard
                footnote="cầu thủ có dữ liệu"
                icon="up"
                label="Cầu thủ"
                value={network.nodes.length}
              />
              <StatCard
                footnote="liên kết chuyền"
                icon="up"
                label="Số cạnh"
                value={network.edges.length}
              />
              <StatCard
                footnote={
                  strongestEdge && strongestEdge.count
                    ? `${getSurname(strongestEdge.source)} → ${getSurname(strongestEdge.target)}`
                    : "Chưa có liên kết"
                }
                icon="up"
                label="Cạnh mạnh nhất"
                value={strongestEdge?.count ?? 0}
              />
            </section>

            <section className="players-card card-surface">
              <div className="panel-heading players-heading">
                <div>
                  <h3>Cầu thủ chuyền nhiều</h3>
                  <p>Thống kê theo số đường chuyền</p>
                </div>
                <span className="table-unit">LẦN</span>
              </div>
              <div className="player-table">
                {topPlayers.map((player, index) => (
                  <div className="player-row" key={player.player}>
                    <span className="player-rank">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <span className="player-name" title={player.player}>
                      {player.short_name}
                    </span>
                    <span className="player-passes">{player.pass_count}</span>
                    <span className="player-bar-track">
                      <span
                        className="player-bar"
                        style={{
                          width: `${Math.max(5, (player.pass_count / Math.max(1, topPlayers[0]?.pass_count ?? 1)) * 100)}%`,
                        }}
                      />
                    </span>
                  </div>
                ))}
                {topPlayers.length === 0 && (
                  <div className="empty-players">Chưa có dữ liệu cầu thủ.</div>
                )}
              </div>
            </section>
          </aside>
        </div>
      ) : (
        <AnimatePresence mode="wait">
          {!networkQuery.isError && (
            <motion.div
              animate={{ opacity: 1 }}
              className="loading-inline card-surface"
              exit={{ opacity: 0 }}
              initial={{ opacity: 0 }}
            >
              <LoaderCircle aria-hidden="true" className="spin" size={18} />
              Đang kết nối dữ liệu trận đấu
            </motion.div>
          )}
        </AnimatePresence>
      )}
    </motion.div>
  )
}
