import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { fetchStats } from '../api.js'
import BarList from '../components/BarList.jsx'
import ColumnChart from '../components/ColumnChart.jsx'
import RegionTypeTable from '../components/RegionTypeTable.jsx'
import { todayYmd } from '../dates.js'

export default function StatsPage() {
  const [params, setParams] = useSearchParams()
  const [activeOnly, setActiveOnly] = useState(true)
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setError('')
    fetchStats({ active_only: activeOnly })
      .then(setStats)
      .catch((e) => setError(e.message))
  }, [activeOnly])

  if (error) return <p className="notice notice-error">통계를 불러오지 못했습니다: {error}</p>
  if (!stats) return <p className="empty">불러오는 중…</p>

  const region = params.get('region') || stats.by_region[0]?.key || ''
  const setRegion = (r) => {
    setParams({ region: r }, { replace: true })
  }
  const currentMonth = todayYmd().slice(0, 6)

  return (
    <section>
      <div className="hero hero-row">
        <div>
          <h1>식품안심업소 지정 현황</h1>
          <p>지역·업종·지정기관별 분포와 지정 추이를 살펴보세요.</p>
        </div>
        <label className="toggle">
          <input type="checkbox" checked={activeOnly} onChange={(e) => setActiveOnly(e.target.checked)} />
          영업 중인 업소만
        </label>
      </div>

      {stats.total === 0 ? (
        <p className="notice">
          아직 집계할 데이터가 없습니다.{' '}
          {stats.sync?.status === 'running' ? '동기화가 진행 중입니다.' : stats.sync?.message || ''}
        </p>
      ) : (
        <>
          <div className="tiles">
            <div className="tile">
              <span className="tile-label">{activeOnly ? '영업 중 지정업소' : '전체 지정업소'}</span>
              <span className="tile-value">{stats.total.toLocaleString()}</span>
            </div>
            <Link className="tile tile-link" to="/?exp=1">
              <span className="tile-label">
                <span className="status-dot warning" aria-hidden="true" />
                만료 3개월 이내
              </span>
              <span className="tile-value">{stats.expiring.toLocaleString()}</span>
              <span className="tile-sub">목록 보기 →</span>
            </Link>
            <div className="tile">
              <span className="tile-label">지역 수</span>
              <span className="tile-value">{stats.by_region.length}</span>
            </div>
            <div className="tile">
              <span className="tile-label">업종 수</span>
              <span className="tile-value">{stats.by_type.length}</span>
            </div>
          </div>

          <RegionTypeTable
            regions={stats.by_region}
            region={region}
            onRegionChange={setRegion}
            activeOnly={activeOnly}
          />

          <div className="panels">
            <div className="panel panel-wide">
              <div className="panel-head">
                <h2>연도별 지정 추이</h2>
                <div className="year-chips">
                  {stats.by_year.map((y) => (
                    <span key={y.key} className="year-chip">
                      <span className="muted">{y.key}년</span> <strong>{y.count.toLocaleString()}</strong>곳
                    </span>
                  ))}
                </div>
              </div>
              <ColumnChart items={stats.by_month} currentMonth={currentMonth} />
              <p className="muted small">월별 신규 지정 건수 (지정일자 기준). 이번 달은 집계 중이라 옅게 표시합니다.</p>
            </div>
            <div className="panel">
              <h2>업종별</h2>
              <BarList items={stats.by_type} total={stats.total} limit={8} />
            </div>
            <div className="panel">
              <h2>지정기관별</h2>
              <BarList items={stats.by_agency} total={stats.total} limit={6} />
            </div>
            <div className="panel panel-wide">
              <h2>지역별</h2>
              <BarList
                items={stats.by_region}
                total={stats.total}
                onSelect={(r) => {
                  setRegion(r.key)
                  document.querySelector('.rt')?.scrollIntoView({ behavior: 'smooth' })
                }}
              />
              <p className="muted small">지역 막대를 누르면 위의 지역 × 업종 표가 그 지역으로 바뀝니다.</p>
            </div>
          </div>

          <details className="panel table-view">
            <summary>표로 보기</summary>
            <div className="tables">
              {[
                ['업종', stats.by_type],
                ['지정기관', stats.by_agency],
                ['지역', stats.by_region],
                ['지정연도', stats.by_year],
              ].map(([title, rows]) => (
                <table key={title}>
                  <thead>
                    <tr>
                      <th>{title}</th>
                      <th>업소 수</th>
                      <th>비율</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr key={r.key}>
                        <td>{r.key}</td>
                        <td>{r.count.toLocaleString()}</td>
                        <td>{((r.count / stats.total) * 100).toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ))}
            </div>
          </details>

          <p className="muted small">
            {stats.sync?.finished_at && `데이터 갱신 ${new Date(stats.sync.finished_at).toLocaleString('ko-KR')} · `}
            <Link to="/">업소 검색으로 이동</Link>
          </p>
        </>
      )}
    </section>
  )
}
