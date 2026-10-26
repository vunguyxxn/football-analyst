import { useQuery } from "@tanstack/react-query"
import { motion } from "framer-motion"
import {
  Activity,
  ChartNoAxesCombined,
  Clapperboard,
  ClipboardList,
  LayoutDashboard,
  UserRound,
} from "lucide-react"
import { NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom"
import { ComingSoon } from "@/components/ComingSoon"
import MatchAnalysis from "@/pages/MatchAnalysis"
import VideoAnalysis from "@/pages/VideoAnalysis"
import { fetchHealth } from "@/lib/api"

const navigation = [
  { label: "Tổng quan", path: "/overview", icon: LayoutDashboard },
  { label: "Phân tích trận", path: "/match", icon: ChartNoAxesCombined },
  { label: "Phân tích video", path: "/video", icon: Clapperboard },
  { label: "Hồ sơ cầu thủ", path: "/players", icon: UserRound },
  { label: "Báo cáo HLV", path: "/reports", icon: ClipboardList },
]

function AppShell() {
  const location = useLocation()
  const activePage =
    navigation.find((item) => item.path === location.pathname) ?? navigation[0]
  const health = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    retry: false,
    refetchInterval: 5000,
  })
  const isHealthy = health.data?.status === "ok" && !health.isError

  return (
    <div className="app-shell">
      <aside aria-label="Điều hướng chính" className="sidebar">
        <NavLink aria-label="Football Analyst" className="brand" to="/overview">
          <span className="brand-mark">
            <Activity aria-hidden="true" size={21} strokeWidth={2.5} />
          </span>
          <span className="brand-copy">
            <strong>TOUCHLINE</strong>
            <small>FOOTBALL ANALYST</small>
          </span>
        </NavLink>

        <div className="sidebar-section-label">WORKSPACE</div>
        <nav className="side-navigation">
          {navigation.map(({ icon: Icon, label, path }) => (
            <NavLink
              aria-label={label}
              className={({ isActive }) =>
                `side-link${isActive ? " active" : ""}`
              }
              key={path}
              title={label}
              to={path}
            >
              <Icon aria-hidden="true" size={19} strokeWidth={1.8} />
              <span>{label}</span>
              {path === "/match" && <i aria-hidden="true" />}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="club-emblem">FA</div>
          <div className="profile-copy">
            <strong>Đội ngũ phân tích</strong>
            <span>Không gian làm việc</span>
          </div>
          <span className="profile-menu" aria-hidden="true">•••</span>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumbs">
            <span className="crumb-root">Workspace</span>
            <span className="crumb-slash">/</span>
            <h1>{activePage.label}</h1>
          </div>
          <div
            aria-live="polite"
            className={`backend-indicator${isHealthy ? " is-online" : health.isError ? " is-offline" : ""}`}
            title={
              isHealthy
                ? "Backend đang hoạt động"
                : health.isError
                  ? "Không thể kết nối backend"
                  : "Đang kiểm tra backend"
            }
          >
            <span className="status-dot" />
            {isHealthy ? "Backend: OK" : health.isError ? "Backend: lỗi" : "Backend: …"}
          </div>
        </header>

        <main className="main-content">
          <motion.div
            animate={{ opacity: 1, y: 0 }}
            className="route-container"
            initial={{ opacity: 0, y: 8 }}
            key={location.pathname}
            transition={{ duration: 0.2 }}
          >
            <Routes location={location}>
              <Route element={<Navigate replace to="/overview" />} path="/" />
              <Route
                element={<ComingSoon icon={LayoutDashboard} title="Tổng quan" />}
                path="/overview"
              />
              <Route element={<MatchAnalysis />} path="/match" />
              <Route
                element={<VideoAnalysis />}
                path="/video"
              />
              <Route
                element={<ComingSoon icon={UserRound} title="Hồ sơ cầu thủ" />}
                path="/players"
              />
              <Route
                element={<ComingSoon icon={ClipboardList} title="Báo cáo HLV" />}
                path="/reports"
              />
              <Route
                element={<ComingSoon icon={LayoutDashboard} title="Tổng quan" />}
                path="*"
              />
            </Routes>
          </motion.div>
          <footer className="app-footer">
            <span>TOUCHLINE ANALYTICS</span>
            <span>STATSBOMB OPEN DATA</span>
          </footer>
        </main>
      </div>
    </div>
  )
}

export default AppShell
