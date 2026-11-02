import { useState } from "react"
import { ArrowUpRight, ClipboardList, Layers } from "lucide-react"
import { Button } from "@/components/ui/button"
import { COACH_LABELS, type CoachCard, type CoachTeam } from "@/lib/coachReport"
import { formatProfileMetric as metric } from "@/lib/playerProfiles"

function GroupEvidence({ card }: { card: CoachCard }) {
  return <details className="coach-group-evidence">
    <summary>Xem SHAP trung bình của nhóm</summary>
    <div className="coach-group-row"><span>Feature</span><span>Giá trị TB</span><span>SHAP TB</span></div>
    {card.support.map(key => <div className="coach-group-row" key={key}>
      <span>{COACH_LABELS[key]}</span><strong>{metric(card.meanFeatures[key], 3)}</strong>
      <strong>{card.meanShap[key] > 0 ? "+" : ""}{metric(card.meanShap[key], 4)}</strong>
    </div>)}
    <p>SHAP trung bình có đơn vị log-odds, không phải phần trăm cải thiện.</p>
  </details>
}

export default function CoachRecommendations({ team, selected, allShots, onSelect }: {
  team: CoachTeam
  selected: CoachCard | undefined
  allShots: boolean
  onSelect: (id: string) => void
}) {
  const [view, setView] = useState<"cards" | "table">("cards")
  const isSelected = (card: CoachCard) => selected?.id === card.id && !allShots
  return <section className="coach-recommendations">
    <div className="coach-section-heading">
      <h3><ClipboardList size={17} />Điều cần xem lại</h3>
      <div className="coach-view-toggle" role="group" aria-label="Cách xem gợi ý">
        <button aria-pressed={view === "cards"} onClick={() => setView("cards")}>Thẻ</button>
        <button aria-pressed={view === "table"} onClick={() => setView("table")}>Bảng</button>
      </div>
    </div>
    <p className="coach-caption">Luật cố định + xG + SHAP. Tỷ lệ nhóm là căn cứ quan sát, không phải độ tin cậy của AI.</p>
    {!team.cards.length ? <div className="coach-empty card-surface">
      {team.status === "insufficient_data" ? "Chưa đủ cú sút hợp lệ để sinh gợi ý." : "Chưa có luật nào đủ điều kiện. Không có gợi ý không đồng nghĩa đội chơi tốt."}
    </div> : view === "table" ? <>
      <div className="coach-table-scroll card-surface" tabIndex={0} role="region" aria-label="Bảng gợi ý rà soát">
        <table className="coach-recommendation-table">
          <caption>Gợi ý của {team.name}; chọn một dòng để xem cùng các cú sút và giải thích bên dưới.</caption>
          <thead><tr><th scope="col">Điều cần xem lại</th><th scope="col">Nhóm căn cứ</th><th scope="col">Cú sút / tổng</th><th scope="col">Tỷ lệ nhóm</th><th scope="col">xG nhóm</th><th scope="col">Căn cứ</th></tr></thead>
          <tbody>{team.cards.map(card => <tr key={card.id} className={isSelected(card) ? "selected" : ""}>
            <th scope="row"><strong>{card.title}</strong><p>{card.action}</p></th>
            <td>{card.criterion}</td><td>{card.shots.length}/{team.shots.length}</td>
            <td>{metric(card.fraction * 100, 1)}%</td><td>{metric(card.meanXg, 3)}</td>
            <td><Button aria-pressed={isSelected(card)} variant="outline" onClick={() => onSelect(card.id)}>Xem {card.shots.length} cú sút</Button></td>
          </tr>)}</tbody>
        </table>
      </div>
      {selected && <div className="coach-table-group card-surface"><strong>Căn cứ nhóm: {selected.title}</strong><GroupEvidence card={selected} /></div>}
    </> : team.cards.map(card => <article className={`coach-recommendation card-surface${isSelected(card) ? " selected" : ""}`} key={card.id}>
      <div className="coach-card-number"><Layers size={18} /></div>
      <div className="coach-card-copy">
        <h4>{card.title}</h4><p>{card.action}</p>
        <div className="coach-card-facts"><span>{card.criterion}</span><span><strong>{card.shots.length}/{team.shots.length}</strong> cú sút ({metric(card.fraction * 100, 1)}%)</span><span>xG nhóm <strong>{metric(card.meanXg, 3)}</strong></span></div>
        <small>Tỷ lệ nhóm làm căn cứ, không phải độ tin cậy của AI.</small>
        <GroupEvidence card={card} />
      </div>
      <Button aria-pressed={isSelected(card)} onClick={() => onSelect(card.id)} variant="outline">Xem {card.shots.length} cú sút căn cứ<ArrowUpRight size={14} /></Button>
    </article>)}
  </section>
}
