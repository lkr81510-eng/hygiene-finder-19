import { NavLink, Route, Routes } from 'react-router-dom'
import SearchPage from './pages/SearchPage.jsx'
import StatsPage from './pages/StatsPage.jsx'

export default function App() {
  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-inner">
          <NavLink to="/" className="brand">
            <span className="brand-mark" aria-hidden="true">✓</span>
            위생등급 조회
          </NavLink>
          <nav className="tabs" aria-label="주 메뉴">
            <NavLink to="/" end className="tab">
              업소 검색
            </NavLink>
            <NavLink to="/stats" className="tab">
              통계
            </NavLink>
          </nav>
        </div>
        <p className="tagline">
          식약처 식품안심업소(위생등급) 지정 현황 기반 · 창업 예정자를 위한 지역별 위생 우수업소 현황
        </p>
      </header>
      <main className="container">
        <Routes>
          <Route path="/" element={<SearchPage />} />
          <Route path="/stats" element={<StatsPage />} />
          <Route path="*" element={<p className="empty">페이지를 찾을 수 없습니다.</p>} />
        </Routes>
      </main>
      <footer className="footer">
        자료: 식품의약품안전처 식품안전나라 오픈API (C004 식품접객업소 식품안심업소(위생등급) 지정 현황)
      </footer>
    </div>
  )
}
