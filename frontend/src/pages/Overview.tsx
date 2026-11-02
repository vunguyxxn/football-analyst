import { ArrowUpRight, ChartNoAxesCombined, Clapperboard, ClipboardList, Waypoints } from "lucide-react"
import { Link } from "react-router-dom"

const actions = [
  { path: "/video", icon: Clapperboard, label: "Phân tích video", note: "Mở clip của bạn hoặc xem mẫu đã xử lý. Theo dõi người, xem vị trí và phân tích trên đoạn đủ dữ liệu.", tag: "VIDEO & CHUYỂN ĐỘNG" },
  { path: "/match", icon: ChartNoAxesCombined, label: "Khám phá một trận đấu", note: "Chọn trận từ StatsBomb, đọc chỉ số sự kiện và xem các kết nối chuyền bóng.", tag: "DỮ LIỆU SỰ KIỆN" },
  { path: "/tactics", icon: Waypoints, label: "Chuẩn bị phương án chiến thuật", note: "Bố trí hai đội, vẽ đường di chuyển và xây dựng các pha cho buổi tập.", tag: "COACH STUDIO" },
  { path: "/reports", icon: ClipboardList, label: "Đọc báo cáo HLV", note: "Mở báo cáo đã xử lý, xem điều cần rà soát và các tình huống làm căn cứ.", tag: "BÁO CÁO & CĂN CỨ" },
] as const

export default function Overview() {
  return <div className="overview-page">
    <section className="overview-hero">
      <span className="eyebrow">TOUCHLINE · KHÔNG GIAN PHÂN TÍCH</span>
      <h2>Hiểu trận đấu.<br /><span>Chuẩn bị bước tiếp theo.</span></h2>
      <p>Bắt đầu từ video, dữ liệu trận đấu hoặc một ý tưởng chiến thuật. Mỗi kết quả đều đi cùng nguồn và phạm vi quan sát.</p>
      <Link className="overview-primary" to="/video"><Clapperboard size={18} />Bắt đầu với video<ArrowUpRight size={18} /></Link>
      <div className="overview-pitch-art" aria-hidden="true"><i /><b /></div>
    </section>
    <div className="overview-section-heading"><h3>Bạn muốn làm gì hôm nay?</h3><span>Chọn một luồng làm việc</span></div>
    <section className="overview-actions" aria-label="Bắt đầu phân tích">
      {actions.map(({ path, icon: Icon, label, note, tag }) => <Link to={path} className="overview-action card-surface" key={path}>
        <span className="overview-action-icon"><Icon size={23} /></span><ArrowUpRight className="overview-action-arrow" size={20} />
        <small>{tag}</small><h3>{label}</h3><p>{note}</p><span className="overview-action-open">Mở không gian làm việc →</span>
      </Link>)}
    </section>
    <aside className="overview-source-note"><strong>Đọc kết quả trong đúng ngữ cảnh</strong><p>StatsBomb và Metrica là nguồn dữ liệu riêng. Kết quả từ video là ước lượng theo đoạn đã hiệu chỉnh; bảng chiến thuật là bố trí thủ công.</p></aside>
  </div>
}
