import { useEffect, useRef, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { motion, MotionConfig } from "framer-motion"
import {
  Activity,
  Menu,
  X,
  ChartNoAxesCombined,
  Clapperboard,
  ClipboardList,
  LayoutDashboard,
  UserRound,
  Waypoints,
} from "lucide-react"
import { NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom"
import Overview from "@/pages/Overview"
import MatchAnalysis from "@/pages/MatchAnalysis"
import VideoAnalysis from "@/pages/VideoAnalysis"
import PlayerProfiles from "@/pages/PlayerProfiles"
import CoachReport from "@/pages/CoachReport"
import TacticsBoard from "@/pages/TacticsBoard"
import { fetchHealth } from "@/lib/api"

const navigation = [
  { label: "Tổng quan", path: "/overview", icon: LayoutDashboard },
  { label: "Phân tích trận", path: "/match", icon: ChartNoAxesCombined },
  { label: "Phân tích video", path: "/video", icon: Clapperboard },
  { label: "Hồ sơ cầu thủ", path: "/players", icon: UserRound },
  { label: "Báo cáo HLV", path: "/reports", icon: ClipboardList },
  { label: "Bảng chiến thuật", path: "/tactics", icon: Waypoints },
]

function AppShell() {
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)
  const navigationTrigger = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    if (!menuOpen) return
    const trigger = navigationTrigger.current
    const panel = document.getElementById("main-navigation")!
    const controls = () => [...panel.querySelectorAll<HTMLElement>("a,button")].filter(el => el.getBoundingClientRect().width > 0)
    controls()[0]?.focus()
    const overflow = document.body.style.overflow
    document.body.style.overflow = "hidden"
    function keys(event: KeyboardEvent) {
      if (event.key === "Escape") setMenuOpen(false)
      if (event.key !== "Tab") return
      const items = controls(), first = items[0], last = items.at(-1)
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
    }
    function resize() { if (window.innerWidth > 767) setMenuOpen(false) }
    document.addEventListener("keydown", keys)
    window.addEventListener("resize", resize)
    return () => {
      document.body.style.overflow = overflow
      document.removeEventListener("keydown", keys)
      window.removeEventListener("resize", resize)
      trigger?.focus()
    }
  }, [menuOpen])
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
    <MotionConfig reducedMotion="user"><div className={`app-shell${menuOpen ? " navigation-open" : ""}`}>
      {menuOpen && <button className="navigation-backdrop" tabIndex={-1} aria-hidden="true" onClick={() => setMenuOpen(false)} />}
      <aside id="main-navigation" aria-label="Điều hướng chính" className="sidebar">
        <button className="navigation-close" aria-label="Đóng điều hướng" onClick={() => setMenuOpen(false)}><X size={20} /></button>
        <NavLink aria-label="Football Analyst" className="brand" to="/overview" onClick={() => setMenuOpen(false)}>
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
              onClick={() => setMenuOpen(false)}
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

        </div>
      </aside>

      <div className="workspace" inert={menuOpen}>
        <header className="topbar">
          <button ref={navigationTrigger} className="navigation-toggle" aria-label={menuOpen ? "Đóng điều hướng" : "Mở điều hướng"} aria-expanded={menuOpen} aria-controls="main-navigation" onClick={() => setMenuOpen(!menuOpen)}><Menu size={20} /></button>
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
            {isHealthy ? "Máy chủ sẵn sàng" : health.isError ? "Mất kết nối" : "Đang kết nối…"}
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
                element={<Overview />}
                path="/overview"
              />
              <Route element={<MatchAnalysis />} path="/match" />
              <Route element={<TacticsBoard />} path="/tactics" />
              <Route
                element={<VideoAnalysis />}
                path="/video"
              />
              <Route
                element={<PlayerProfiles />}
                path="/players"
              />
              <Route
                element={<CoachReport />}
                path="/reports"
              />
              <Route
                element={<Overview />}
                path="*"
              />
            </Routes>
          </motion.div>
          <footer className="app-footer">
            <span>TOUCHLINE ANALYTICS</span>
            <span>PHÂN TÍCH · ĐỐI CHIẾU · HUẤN LUYỆN</span>
          </footer>
        </main>
      </div>
    </div></MotionConfig>
  )
}

export default AppShell
