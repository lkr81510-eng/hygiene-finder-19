import ExpiryBadge from './ExpiryBadge.jsx'
import { fmtYmd } from '../dates.js'

export default function ShopCard({ shop, today, windowDays }) {
  const from = fmtYmd(shop.asgn_from || shop.hg_asgn_ymd)
  const to = fmtYmd(shop.asgn_to)
  return (
    <article className={`card${shop.is_active ? '' : ' inactive'}`}>
      <div className="card-head">
        <h3 className="card-title">{shop.bssh_nm || '(업소명 없음)'}</h3>
        <ExpiryBadge asgnTo={shop.asgn_to} today={today} windowDays={windowDays} />
      </div>
      <div className="card-meta">
        {shop.induty_nm && <span className="chip">{shop.induty_nm}</span>}
        {shop.sido && (
          <span className="chip">
            {shop.sido}
            {shop.sigungu ? ` ${shop.sigungu}` : ''}
          </span>
        )}
        {!shop.is_active && <span className="chip chip-warn">{shop.clsbiz_dvs_cd_nm || '지정 해제'}</span>}
      </div>
      {shop.addr && <p className="card-addr">{shop.addr}</p>}
      <dl className="card-info">
        {shop.telno && (
          <>
            <dt>전화</dt>
            <dd>
              <a href={`tel:${shop.telno.replace(/[^\d+]/g, '')}`}>{shop.telno}</a>
            </dd>
          </>
        )}
        {from && (
          <>
            <dt>지정기간</dt>
            <dd>
              {from}
              {to ? ` ~ ${to}` : ''}
            </dd>
          </>
        )}
        {shop.hg_asgn_nm && (
          <>
            <dt>지정기관</dt>
            <dd>{shop.hg_asgn_nm}</dd>
          </>
        )}
      </dl>
    </article>
  )
}
