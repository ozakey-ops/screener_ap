"""
KRX 주식 스크리너 — Streamlit 버전
배포: Streamlit Community Cloud (streamlit.io)
Secrets: KRX_API_KEY / DART_API_KEY
"""

import os, threading, zipfile, io
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import xml.etree.ElementTree as ET
import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# ─────────────────────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="KRX 주식 스크리너",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  /* ── 전역 배경 / 폰트 ── */
  .stApp { background:#f0f3fa; }
  .block-container { padding-top: 5rem !important; padding-bottom:1rem;
    max-width:1200px; }
  /* Streamlit 상단바 투명 처리 */
  header[data-testid="stHeader"] {
    background:rgba(240,243,250,0.97) !important;
    border-bottom:1px solid #dde1ec;
    backdrop-filter:blur(8px);
  }
  /* 툴바 아이콘 색 */
  header[data-testid="stHeader"] button { color:#5d6278 !important; }

  /* ── KRX 로고 헤더 바 ── */
  .tv-topbar {
    display:flex; align-items:center; gap:12px;
    background:#ffffff; border:1px solid #dde1ec;
    border-radius:10px; padding:10px 16px; margin-bottom:12px;
    box-shadow:0 2px 6px rgba(0,0,0,.05);
  }
  .tv-logo { font-size:18px; font-weight:800; color:#131722;
    letter-spacing:-.5px; white-space:nowrap; }
  .tv-logo span { color:#1a6fe8; }
  .tv-date { font-size:11px; color:#9da3b4; margin-left:auto; white-space:nowrap; }

  /* ── 필터 바 ── */
  /* ── 우량주 조건 패널 ── */
  .quality-panel {
    background:#f0f6ff; border:1px solid #b8d0f7; border-radius:10px;
    padding:10px 16px; margin-bottom:10px;
    box-shadow:0 1px 4px rgba(26,111,232,.08);
  }


  /* ── 종목 수 ── */
  .tv-count { font-size:12px; color:#5d6278; padding:4px 0 6px; }

  /* ── 지표 카드 ── */
  .metric-card {
    background:#ffffff; border:1px solid #dde1ec;
    border-radius:10px; padding:14px 10px; text-align:center;
    box-shadow:0 1px 4px rgba(0,0,0,.04);
  }
  .metric-label { font-size:11px; color:#5d6278; margin-bottom:4px;
    font-weight:600; letter-spacing:.3px; }
  .metric-value { font-size:20px; font-weight:800; color:#131722;
    font-variant-numeric:tabular-nums; }
  .metric-formula { font-size:9px; color:#b0b5c5; margin-top:4px; }

  /* ── Streamlit metric 카드 ── */
  div[data-testid="stMetric"] {
    background:#ffffff !important; border-radius:10px;
    border:1px solid #dde1ec; padding:10px 12px;
    box-shadow:0 1px 4px rgba(0,0,0,.04);
  }
  div[data-testid="stMetricValue"] { color:#131722 !important;
    font-weight:800 !important; }

  /* ── 데이터프레임 ── */
  .stDataFrame { border-radius:10px; overflow:hidden;
    border:1px solid #dde1ec !important;
    box-shadow:0 2px 8px rgba(0,0,0,.05); }
  /* 헤더·셀 가운데 정렬 (HTML 렌더 방식) */
  div[data-testid="stDataFrame"] th,
  div[data-testid="stDataFrame"] td {
    text-align: center !important;
  }
  /* glide-data-grid 헤더 가운데 */
  div[data-testid="stDataFrame"] [role="columnheader"] {
    justify-content: center !important;
    text-align: center !important;
    align-items: center !important;
  }
  div[data-testid="stDataFrame"] [role="columnheader"] > * {
    justify-content: center !important;
    text-align: center !important;
    width: 100% !important;
  }
  /* glide-data-grid 셀 */
  div[data-testid="stDataFrame"] [role="gridcell"] {
    justify-content: center !important;
    text-align: center !important;
    align-items: center !important;
    display: flex !important;
  }
  /* 종목명(2번째 열) 가운데 정렬 */
  div[data-testid="stDataFrame"] [aria-colindex="2"] {
    justify-content: center !important;
    text-align: center !important;
  }


  /* ── 입력 필드 ── */
  .stTextInput input {
    background:#f8f9fc !important; border:1px solid #dde1ec !important;
    border-radius:20px !important; color:#131722 !important;
    font-size:13px !important;
  }
  .stTextInput input:focus { border-color:#1a6fe8 !important;
    box-shadow:0 0 0 2px rgba(26,111,232,.15) !important; }

  /* ── 버튼 ── */
  .stButton button {
    background:#1a6fe8 !important; color:#fff !important;
    border:none !important; border-radius:8px !important;
    font-weight:600 !important;
  }
  .stButton button:hover { background:#1458c0 !important; }

  /* ── 라디오/체크박스 ── */
  .stRadio label { color:#131722 !important; font-size:13px !important; }
  .stCheckbox label { color:#131722 !important; font-size:13px !important; }

  /* ── 섹션 제목 ── */
  h2, h3 { color:#131722 !important; font-weight:800 !important; }

  /* ── expander ── */
  .streamlit-expanderHeader { background:#f8f9fc !important;
    border-radius:8px; color:#131722 !important; }

  /* ── selectbox ── */
  .stSelectbox select, div[data-baseweb="select"] {
    border-color:#dde1ec !important; border-radius:8px !important;
    background:#ffffff !important; color:#131722 !important;
  }
  /* ── 데이터프레임 체크박스 컬럼 숨기기 ── */
  div[data-testid="stDataFrame"] thead tr th:first-child,
  div[data-testid="stDataFrame"] tbody tr td:first-child {
    display:none !important; width:0 !important; padding:0 !important;
  }


  /* ── 필터 행: 라디오+체크박스 수직 중앙 정렬 + 컨텐츠 너비 밀착 ── */
  [data-testid="stHorizontalBlock"]:has([data-testid="stRadio"]) {
    align-items: center !important;
    gap: 0 !important;
  }
  [data-testid="stHorizontalBlock"]:has([data-testid="stRadio"])
    > [data-testid="stColumn"] {
    flex: 0 0 auto !important;
    width: fit-content !important;
    min-width: 0 !important;
    padding-bottom: 0 !important;
  }
  /* 라디오/체크박스 자체 여백 제거 */
  [data-testid="stHorizontalBlock"]:has([data-testid="stRadio"])
    [data-testid="stRadio"],
  [data-testid="stHorizontalBlock"]:has([data-testid="stRadio"])
    [data-testid="stCheckbox"] {
    margin-bottom: 0 !important;
    padding-bottom: 0 !important;
  }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# API 키 — Streamlit secrets 우선, 환경변수 fallback
# ─────────────────────────────────────────────────────────────
try:
    KRX_API_KEY  = st.secrets["KRX_API_KEY"]
    DART_API_KEY = st.secrets["DART_API_KEY"]
except Exception:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    KRX_API_KEY  = os.environ.get("KRX_API_KEY", "")
    DART_API_KEY = os.environ.get("DART_API_KEY", "")

KRX_BASE  = "https://data-dbg.krx.co.kr"
DART_BASE = "https://opendart.fss.or.kr/api"

# ─────────────────────────────────────────────────────────────
# 공유 캐시 (st.cache_resource — 모든 세션 공유)
# ─────────────────────────────────────────────────────────────
@st.cache_resource
def _shared():
    return {"corp_map": {}, "lock": threading.Lock()}

# ─────────────────────────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────────────────────────
def to_num(v):
    try:
        s = str(v).replace(",", "").strip()
        return float(s) if s not in ("", "-", "N/A", "nan") else 0
    except Exception:
        return 0

def recent_biz_day(offset=-1):
    d = datetime.now()
    cnt = 0
    while cnt > offset:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            cnt -= 1
    return d.strftime("%Y%m%d")

def krx_fetch(endpoint, bas_dd):
    try:
        r = requests.get(KRX_BASE + endpoint,
            params={"basDd": bas_dd},
            headers={"AUTH_KEY": KRX_API_KEY, "Accept": "application/json"},
            timeout=15)
        return r.json().get("OutBlock_1", [])
    except Exception:
        return []

# ─────────────────────────────────────────────────────────────
# 종목 데이터
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def get_all_stocks():
    bas_dd = recent_biz_day(-1)
    prev_dd = recent_biz_day(-2)
    rows = []
    for ep in ["/svc/apis/sto/stk_bydd_trd", "/svc/apis/sto/ksq_bydd_trd"]:
        data = krx_fetch(ep, bas_dd) or krx_fetch(ep, prev_dd)
        rows.extend(data)

    # 주가지표(PBR·DIV·EPS·BPS) 병합 — KRX 별도 엔드포인트
    # KRX는 주가지표를 stk_isu_base_info / ksq_isu_base_info 엔드포인트로 제공
    idx_map: dict = {}
    for ep in ["/svc/apis/sto/stk_isu_base_info", "/svc/apis/sto/ksq_isu_base_info"]:
        for r in krx_fetch(ep, bas_dd) or krx_fetch(ep, prev_dd) or []:
            cd = str(r.get("ISU_CD","") or r.get("ISU_SRT_CD","")).zfill(6)[:6]
            if cd:
                idx_map[cd] = r
    if idx_map:
        for row in rows:
            cd = str(row.get("ISU_CD","")).zfill(6)[:6]
            extra = idx_map.get(cd, {})
            # 기존 키를 덮어쓰지 않고 없는 키만 추가
            for k, v in extra.items():
                if k not in row:
                    row[k] = v

    return rows, bas_dd

def normalize_stocks(raw):
    result = []
    for row in raw:
        code = str(row.get("ISU_CD","") or row.get("shrtCd","")).zfill(6)[:6]
        name = str(row.get("ISU_NM","") or row.get("itmsNm","")).strip()
        mkt  = str(row.get("MKT_NM","") or row.get("mrktCtg","")).upper()
        close= to_num(row.get("TDD_CLSPRC") or row.get("clpr"))
        vol  = to_num(row.get("ACC_TRDVOL") or row.get("trqu"))
        tval = to_num(row.get("ACC_TRDVAL") or row.get("trPrc"))   # 거래대금(원)
        chg  = to_num(row.get("FLUC_RT")   or row.get("fltRt"))
        mc   = to_num(row.get("MKTCAP")     or row.get("mrktTotAmt"))
        shr  = to_num(row.get("LIST_SHRS")  or row.get("lstgStCnt"))
        # KRX 필드명은 버전별로 상이 — 다수 변형 시도
        eps = to_num(row.get("EPS") or row.get("eps") or row.get("EPS_VAL") or 0)
        bps = to_num(row.get("BPS") or row.get("bps") or row.get("BPS_VAL") or 0)
        # DIV: 배당수익률(%) — 필드명 변형 다수 시도
        div = to_num(row.get("DIV") or row.get("div") or row.get("DIV_YLD")
                     or row.get("dvdRt") or row.get("DIV_RT") or 0)
        dps = to_num(row.get("DPS") or row.get("dps") or row.get("DPS_VAL") or 0)
        # PBR: KRX 직접 제공 시 사용, 없으면 현재가/BPS 계산
        pbr_krx = to_num(row.get("PBR") or row.get("pbr") or row.get("PBR_VAL") or 0)
        if pbr_krx > 0:
            pbr = round(pbr_krx, 2)
        elif bps > 0 and close > 0:
            pbr = round(close / bps, 2)
        else:
            pbr = None
        if not code or not name:
            continue
        result.append({"code":code,"name":name,
            "market":"KOSPI" if "KOSPI" in mkt else "KOSDAQ",
            "close":close,"volume":vol,"tval":tval,
            "chg_rt":chg,"mktcap":mc,"shares":shr,
            "eps":eps,"bps":bps,"div":div,"dps":dps,"pbr":pbr})
    return result

# ─────────────────────────────────────────────────────────────
# DART 코드 맵
# ─────────────────────────────────────────────────────────────
def _dart_session():
    s = requests.Session()
    retry = Retry(total=4, backoff_factor=2,
                  status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=["GET"])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s

@st.cache_resource
def get_corp_map():
    sh = _shared()
    if sh["corp_map"]:
        return sh["corp_map"]
    try:
        sess = _dart_session()
        r = sess.get(f"{DART_BASE}/corpCode.xml",
            params={"crtfc_key": DART_API_KEY}, timeout=60)
        r.raise_for_status()
        z = zipfile.ZipFile(io.BytesIO(r.content))
        xml_data = z.read("CORPCODE.xml")
        root = ET.fromstring(xml_data)
        m = {}
        for item in root.findall("list"):
            sc = (item.findtext("stock_code") or "").strip()
            cc = (item.findtext("corp_code")  or "").strip()
            if sc and cc:
                m[sc.zfill(6)] = cc
        if m:
            sh["corp_map"] = m
        return m
    except Exception as e:
        st.warning(f"DART 기업코드 로드 실패 (다시 클릭해 주세요): {e}")
        return {}

# ─────────────────────────────────────────────────────────────
# DART 재무 데이터
# ─────────────────────────────────────────────────────────────
_ACCT = {
    "revenue":      (None, ["매출액","수익(매출액)","영업수익","매출"]),
    "op_income":    (None, ["영업이익","영업이익(손실)"]),
    "net_income":   (None, ["당기순이익","당기순이익(손실)","분기순이익"]),
    "interest_exp": (None, ["이자비용","금융비용","금융원가","이자비용(금융원가)",
                             "금융비용합계","이자 및 할인료","차입원가",
                             "금융비용(이자비용)","이자비용및기타금융원가"]),
    "interest_paid":("CF",  ["이자의지급","이자지급","이자의 지급","이자지급액","이자 지급"]),
    "total_assets": (None, ["자산총계"]),
    "equity":       (None, ["자본총계"]),
    "total_liab":   (None, ["부채총계"]),
    "cur_assets":   (None, ["유동자산"]),
    "cur_liab":     (None, ["유동부채"]),
    "cash":         (None, ["현금및현금성자산","현금 및 현금성자산"]),
    "depreciation": ("CF",  ["감가상각비","유형자산감가상각비","감가상각비와무형자산상각비"]),
    "dividends":    ("CF",  ["배당금지급","현금배당금의지급","배당금의지급","배당금의 지급"]),
}

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_dart_financials(stock_code):
    corp_map = get_corp_map()
    corp_code = corp_map.get(stock_code.zfill(6))
    if not corp_code:
        return {}

    current_year = datetime.now().year
    years = list(range(current_year - 1, current_year - 12, -1))
    result = {}

    def fetch_year(year):
        try:
            r = requests.get(f"{DART_BASE}/fnlttSinglAcntAll.json", params={
                "crtfc_key": DART_API_KEY, "corp_code": corp_code,
                "bsns_year": str(year), "reprt_code": "11011",
                "fs_div": "CFS"
            }, timeout=20)
            items = r.json().get("list", [])
            if not items:
                r2 = requests.get(f"{DART_BASE}/fnlttSinglAcntAll.json", params={
                    "crtfc_key": DART_API_KEY, "corp_code": corp_code,
                    "bsns_year": str(year), "reprt_code": "11011", "fs_div": "OFS"
                }, timeout=20)
                items = r2.json().get("list", [])
            if not items:
                return
            d = {}
            for key, (sj_filter, names) in _ACCT.items():
                for item in items:
                    sj = item.get("sj_div","")
                    nm = item.get("account_nm","").replace(" ","")
                    if sj_filter and sj != sj_filter:
                        continue
                    if any(nm == n.replace(" ","") for n in names):
                        val = to_num(item.get("thstrm_amount","0"))
                        if val != 0:
                            d[key] = val
                            break
            if d:
                result[str(year)] = d
        except Exception:
            pass

    with ThreadPoolExecutor(max_workers=4) as exe:
        list(exe.map(fetch_year, years))

    return {str(k): v for k, v in sorted(result.items())}

# ─────────────────────────────────────────────────────────────
# 연말 시총 (단일 종목)
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400*7, show_spinner=False)
def get_ye_mktcap(stock_code, year):
    code6 = stock_code.zfill(6)
    for delta in range(1, 12):
        candidate = datetime(year, 12, 31) - timedelta(days=delta)
        if candidate.weekday() >= 5:
            continue
        date_str = candidate.strftime("%Y%m%d")
        for ep in ["/svc/apis/sto/stk_bydd_trd", "/svc/apis/sto/ksq_bydd_trd"]:
            try:
                r = requests.get(KRX_BASE + ep,
                    params={"basDd": date_str, "isuCd": code6},
                    headers={"AUTH_KEY": KRX_API_KEY, "Accept": "application/json"},
                    timeout=15)
                rows = r.json().get("OutBlock_1", [])
                for row in rows:
                    if str(row.get("ISU_CD","")).zfill(6)[:6] == code6:
                        mc = to_num(row.get("MKTCAP", 0))
                        if mc > 0:
                            return mc
            except Exception:
                continue
    return 0.0

# ─────────────────────────────────────────────────────────────
# 우량주 재무 요약 (DART 스크리닝용)
# ─────────────────────────────────────────────────────────────
def get_quality_metrics(raw_fin, close: float = 0, shares: float = 0):
    """DART 재무데이터 → ROE·부채비율·영업이익률·PBR·DIV 계산"""
    if not raw_fin:
        return {}
    yr = max(raw_fin.keys())
    d  = raw_fin[yr]
    rv = {}
    rev    = d.get("revenue",      0) or 0
    op_inc = d.get("op_income",    0) or 0
    net    = d.get("net_income",   0) or 0
    eq     = d.get("equity",       0) or 0
    assets = d.get("total_assets", 0) or 0
    divs   = d.get("dividends",    0) or 0  # 현금배당 (CF)
    if rev and op_inc:
        rv["op_margin"]  = round(op_inc / rev * 100, 1)
    if net and eq and abs(eq) > 0:
        rv["roe"]        = round(net / abs(eq) * 100, 1)
    if assets > 0 and eq > 0:
        rv["debt_ratio"] = round((assets - eq) / eq * 100, 0)
    # 재무 스케일 감지 (equity → BPS 역산)
    fin_scale = 1_000_000  # 기본값: 백만원 단위
    if close > 0 and shares > 0 and eq > 0:
        for scale in [1, 1_000, 1_000_000, 100_000_000]:
            bps_val = abs(eq) * scale / shares
            if bps_val > 0 and 0.05 <= close / bps_val <= 100:
                fin_scale = scale
                rv["pbr_dart"] = round(close / bps_val, 2)
                break
    # 영업이익·배당금 (억원)
    if op_inc:
        rv["op_income_eok"] = round(op_inc * fin_scale / 1e8)
    if divs:
        rv["dividends_eok"] = round(abs(divs) * fin_scale / 1e8)
    # DIV: 배당금 / 시가총액 (시가총액 = close * shares)
    if close > 0 and shares > 0 and divs:
        mktcap = close * shares
        for scale in [1, 1_000, 1_000_000]:
            div_pct = abs(divs) * scale / mktcap * 100
            if 0.01 <= div_pct <= 30:
                rv["div_dart"] = round(div_pct, 2)
                break
    return rv

# ─────────────────────────────────────────────────────────────
# 지표 계산
# ─────────────────────────────────────────────────────────────
def compute_ratios(raw_fin, stock):
    stock_code = stock.get("code","")
    mktcap = stock.get("mktcap", 0)
    shares = stock.get("shares", 0)
    close  = stock.get("close",  0)
    years  = sorted(raw_fin.keys())

    def r2(v): return round(v, 2) if v is not None else None

    def _yr_scale(eq_raw, yr_int):
        if not eq_raw or eq_raw <= 0 or shares <= 0:
            return 1_000_000
        ye_mc = get_ye_mktcap(stock_code, yr_int)
        yr_close = (ye_mc / shares) if ye_mc > 0 else close
        if yr_close <= 0:
            return 1_000_000
        for s in [1, 1_000, 1_000_000, 100_000_000]:
            bps = eq_raw * s / shares
            if bps > 0 and 0.05 <= (yr_close / bps) <= 50:
                return s
        return 1_000_000

    def _detect_div_scale(divs_raw, ye_mc):
        if not divs_raw or not ye_mc:
            return None
        for s in [1, 1_000, 1_000_000]:
            if 0.01 <= abs(divs_raw) * s / ye_mc * 100 <= 30:
                return s
        return 1

    latest_scale = _yr_scale(raw_fin[years[-1]].get("equity") if years else None,
                              int(years[-1]) if years else datetime.now().year)

    ratios = {}
    for i, yr in enumerate(years):
        d = raw_fin[yr]; rv = {}
        rev    = d.get("revenue");     op_inc  = d.get("op_income")
        net_inc= d.get("net_income");  assets  = d.get("total_assets")
        equity = d.get("equity");      liab    = d.get("total_liab")
        cur_a  = d.get("cur_assets");  cur_l   = d.get("cur_liab")
        int_exp= d.get("interest_exp") or d.get("interest_paid")
        cash   = d.get("cash");        depre   = d.get("depreciation")
        divs   = d.get("dividends")
        yr_int = int(yr)
        yr_scale = _yr_scale(equity, yr_int)

        if net_inc is not None and equity and equity != 0:
            rv["ROE"] = r2(net_inc / equity * 100)
        if net_inc is not None and assets and assets != 0:
            rv["ROA"] = r2(net_inc / assets * 100)
        if op_inc is not None and rev and rev != 0:
            rv["영업이익률"] = r2(op_inc / rev * 100)
        if liab is not None and equity and equity != 0:
            rv["부채비율"] = r2(liab / equity * 100)
        if cur_a is not None and cur_l and cur_l != 0:
            rv["유동비율"] = r2(cur_a / cur_l * 100)
        if op_inc is not None and int_exp and int_exp != 0:
            rv["이자보상배율"] = r2(op_inc / abs(int_exp))
        if i > 0:
            prev = raw_fin[years[i-1]]
            if rev is not None and prev.get("revenue") and abs(prev["revenue"]) > 0:
                rv["매출액증가율"] = r2((rev - prev["revenue"]) / abs(prev["revenue"]) * 100)
            if op_inc is not None and prev.get("op_income") and abs(prev["op_income"]) > 0:
                rv["영업이익증가율"] = r2((op_inc - prev["op_income"]) / abs(prev["op_income"]) * 100)
        if divs:
            ye_mc = get_ye_mktcap(stock_code, yr_int)
            if ye_mc > 0:
                ds = _detect_div_scale(divs, ye_mc) or yr_scale
                rv["배당수익률"] = r2(abs(divs) * ds / ye_mc * 100)
            elif mktcap > 0 and yr == years[-1]:
                rv["배당수익률"] = r2(abs(divs) * yr_scale / mktcap * 100)
        if yr == years[-1] and mktcap > 0:
            if net_inc:
                nw = net_inc * latest_scale
                if nw > 0: rv["PER"] = r2(mktcap / nw)
            if equity:
                ew = equity * latest_scale
                if ew > 0: rv["PBR"] = r2(mktcap / ew)
            if op_inc and depre is not None and cash is not None and liab is not None:
                ebitda = (op_inc + abs(depre)) * latest_scale
                nd = max(0, liab - cash) * latest_scale
                if ebitda > 0: rv["EV/EBITDA"] = r2((mktcap + nd) / ebitda)
        ratios[yr] = rv
    return ratios

# ─────────────────────────────────────────────────────────────
# UI 헬퍼
# ─────────────────────────────────────────────────────────────
def fmt_mktcap(v):
    """상세 페이지용 — 자동 단위(조/억)"""
    if v >= 1e12: return f"{v/1e12:.1f}조"
    if v >= 1e8:  return f"{v/1e8:.0f}억"
    return f"{v:,.0f}"

def fmt_mktcap_eok(v):
    """테이블용 — 억원 고정"""
    if not v: return 0
    return round(v / 1e8)

def fmt_price(v):
    return f"{int(v):,}" if v else "-"

def make_bar_chart(years, values, title, color):
    fig = go.Figure(go.Bar(
        x=years, y=values,
        marker_color=[color if (v or 0) >= 0 else "#e8394a" for v in values],
        marker_line_width=0,
    ))
    # x축 레이블 겹침 방지: 데이터 수에 따라 각도 조정
    n = len(years)
    tick_angle = -40 if n > 8 else 0
    tick_step  = 2 if n > 10 else 1
    fig.update_layout(
        title=dict(text=title, font_size=13, x=0, xanchor="left",
                   pad=dict(l=4)),
        margin=dict(l=40, r=10, t=36, b=55 if tick_angle else 30),
        height=260, plot_bgcolor="white",
        yaxis=dict(gridcolor="#e8ecf5", zeroline=True, zerolinecolor="#aaa",
                   tickfont_size=10),
        xaxis=dict(tickfont_size=10, tickangle=tick_angle,
                   dtick=tick_step, tickformat="d"),
        showlegend=False,
    )
    return fig

def make_line_chart(years, series, title):
    colors = ["#1a6fe8","#089981","#e8394a","#d4a017"]
    fig = go.Figure()
    for i, (name, vals) in enumerate(series.items()):
        fig.add_trace(go.Scatter(
            x=years, y=vals, name=name,
            line=dict(color=colors[i % len(colors)], width=2.5),
            mode="lines+markers", marker_size=5,
            connectgaps=False,
        ))
    n = len(years)
    tick_angle = -40 if n > 8 else 0
    tick_step  = 2 if n > 10 else 1
    fig.update_layout(
        title=dict(text=title, font_size=13, x=0, xanchor="left",
                   pad=dict(l=4)),
        margin=dict(l=40, r=10, t=36, b=70 if tick_angle else 50),
        height=280, plot_bgcolor="white",
        yaxis=dict(gridcolor="#e8ecf5", tickfont_size=10),
        xaxis=dict(tickfont_size=10, tickangle=tick_angle,
                   dtick=tick_step, tickformat="d"),
        legend=dict(
            font_size=10, orientation="h",
            yanchor="top", y=-0.18,    # 차트 아래쪽 배치
            xanchor="left", x=0,
            bgcolor="rgba(255,255,255,0)",
        ),
    )
    return fig

# ─────────────────────────────────────────────────────────────
# 종목 상세 페이지
# ─────────────────────────────────────────────────────────────
def show_detail(stock):
    if st.button("← 목록으로", key="back_btn"):
        st.session_state.pop("selected", None)
        st.rerun()

    code  = stock["code"]
    name  = stock["name"]
    mkt   = stock["market"]
    close = stock["close"]
    chg   = stock["chg_rt"]
    mc    = stock["mktcap"]

    badge = "K" if mkt == "KOSPI" else "Q"
    st.markdown(f'<div style="font-size:22px;font-weight:800;color:#131722;margin-bottom:8px"><span style="background:{"#deeaff" if mkt=="KOSPI" else "#d5f5ef"};color:{"#1a6fe8" if mkt=="KOSPI" else "#089981"};border-radius:4px;padding:2px 7px;font-size:13px;margin-right:8px">{badge}</span>{name} <span style="color:#9da3b4;font-size:14px">{code}</span></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    _cc = "#089981" if (chg or 0)>0 else "#e8394a" if (chg or 0)<0 else "#5d6278"
    _cs = "+" if (chg or 0)>0 else ""
    _cv = chg if chg is not None else 0.0
    def _card(label, val_html):
        return (f'<div style="background:#fff;border:1px solid #dde1ec;border-radius:10px;'
                f'padding:16px 18px;box-shadow:0 1px 4px rgba(0,0,0,.04);min-height:82px;'
                f'display:flex;flex-direction:column;justify-content:center">'
                f'<div style="font-size:11px;color:#5d6278;font-weight:600;margin-bottom:6px">{label}</div>'
                f'{val_html}</div>')
    with c1:
        st.markdown(_card("현재가",
            f'<div style="display:flex;align-items:baseline;gap:10px">'
            f'<span style="font-size:24px;font-weight:800;color:#131722;font-variant-numeric:tabular-nums">{fmt_price(close)}</span>'
            f'<span style="font-size:14px;font-weight:700;color:{_cc}">{_cs}{_cv:.2f}%</span></div>'),
            unsafe_allow_html=True)
    with c2:
        st.markdown(_card("시가총액",
            f'<div style="font-size:24px;font-weight:800;color:#131722">{fmt_mktcap(mc)}</div>'),
            unsafe_allow_html=True)
    with c3:
        _mc = "#1a6fe8" if mkt=="KOSPI" else "#089981"
        st.markdown(_card("시장",
            f'<div style="font-size:24px;font-weight:800;color:{_mc}">{mkt}</div>'),
            unsafe_allow_html=True)

    # DART 재무
    with st.spinner("재무 데이터 수집 중..."):
        raw_fin = fetch_dart_financials(code)

    if not raw_fin:
        st.warning("재무 데이터를 찾을 수 없습니다.")
        return

    ratios = compute_ratios(raw_fin, stock)
    years  = sorted(ratios.keys())

    def get_series(key):
        return [ratios[y].get(key) for y in years]

    # ── 밸류에이션 ──
    st.subheader("밸류에이션")
    latest = ratios.get(years[-1], {})
    vc = st.columns(3)
    for col, (k, formula) in zip(vc, [
        ("PER","시총÷순이익"), ("PBR","시총÷자기자본"), ("EV/EBITDA","(시총+차입금)÷EBITDA")
    ]):
        v = latest.get(k)
        col.markdown(f"""<div class="metric-card">
            <div class="metric-label">{k}</div>
            <div class="metric-value">{f"{v:.1f}배" if v else "-"}</div>
            <div class="metric-formula">{formula}</div>
        </div>""", unsafe_allow_html=True)

    # ── 수익성 ──
    st.subheader("수익성")
    prof_series = {}
    for k in ["ROE","ROA","영업이익률"]:
        s = get_series(k)
        if any(v is not None for v in s):
            prof_series[k] = s
    if prof_series:
        st.plotly_chart(make_line_chart(years, prof_series, "수익성 추이 (%)"),
                        use_container_width=True, key="prof_chart")

    # ── 성장성 ──
    st.subheader("성장성")
    gc1, gc2 = st.columns(2)
    rev_s = get_series("매출액증가율")
    op_s  = get_series("영업이익증가율")
    if any(v is not None for v in rev_s):
        gc1.plotly_chart(make_bar_chart(years, rev_s, "매출 성장률 (%)", "#1a6fe8"),
                         use_container_width=True, key="rev_chart")
    if any(v is not None for v in op_s):
        gc2.plotly_chart(make_bar_chart(years, op_s, "영업이익 성장률 (%)", "#089981"),
                         use_container_width=True, key="op_chart")

    # ── 재무건전성 ──
    st.subheader("재무건전성")
    stab_series = {}
    for k in ["부채비율","유동비율"]:
        s = get_series(k)
        if any(v is not None for v in s):
            stab_series[k] = s
    if stab_series:
        st.plotly_chart(make_line_chart(years, stab_series, "재무건전성 추이 (%)"),
                        use_container_width=True, key="stab_chart")
    icr = get_series("이자보상배율")
    if any(v is not None for v in icr):
        st.plotly_chart(make_bar_chart(years, icr, "이자보상배율 (배)", "#d4a017"),
                        use_container_width=True, key="icr_chart")

    # ── 배당수익률 ──
    div_s = get_series("배당수익률")
    if any(v is not None for v in div_s):
        st.subheader("배당수익률")
        st.plotly_chart(make_bar_chart(years, div_s, "배당수익률 (%)", "#7c4dff"),
                        use_container_width=True, key="div_chart")

    # ── 원시 재무 테이블 ──
    with st.expander("재무 수치 상세"):
        rows = []
        for yr in years:
            d = raw_fin[yr]
            sc = 1_000_000
            eq = d.get("equity")
            if eq:
                for s in [1, 1_000, 1_000_000, 100_000_000]:
                    bps = eq * s / (stock["shares"] or 1)
                    if bps > 0 and 0.05 <= (close / bps) <= 50:
                        sc = s; break
            rows.append({
                "연도": yr,
                "매출액(억)": round(d["revenue"]*sc/1e8) if d.get("revenue") else None,
                "영업이익(억)": round(d["op_income"]*sc/1e8) if d.get("op_income") else None,
                "순이익(억)": round(d["net_income"]*sc/1e8) if d.get("net_income") else None,
                "자기자본(억)": round(d["equity"]*sc/1e8) if d.get("equity") else None,
                "총자산(억)": round(d["total_assets"]*sc/1e8) if d.get("total_assets") else None,
            })
        st.dataframe(pd.DataFrame(rows).set_index("연도"),
                     use_container_width=True)

# ─────────────────────────────────────────────────────────────
# 메인 앱
# ─────────────────────────────────────────────────────────────
def main():
    # 종목 상세 보기 중이면 상세 페이지 렌더
    if "selected" in st.session_state:
        show_detail(st.session_state["selected"])
        return

    # ── 헤더 ──
    search = st.text_input("검색", placeholder="🔍  종목명 또는 코드 검색...",
                            label_visibility="collapsed")

    # ── 데이터 로드 ──
    with st.spinner("KRX 데이터 수집 중..."):
        try:
            raw, bas_dd = get_all_stocks()
        except Exception as e:
            st.error(f"KRX API 오류: {e}")
            st.stop()
        stocks = normalize_stocks(raw)
        if not stocks:
            st.warning("⚠️ KRX에서 종목 데이터를 가져오지 못했습니다. "
                       "API 키를 확인하거나 잠시 후 다시 시도해 주세요.")
            st.code(f"조회일: {bas_dd}\n수신 raw 건수: {len(raw)}")
            if st.button("🔄 새로고침"):
                st.cache_data.clear()
                st.rerun()
            st.stop()

    date_disp = f"{bas_dd[:4]}.{bas_dd[4:6]}.{bas_dd[6:]}"
    st.markdown(f"""
    <div class="tv-topbar">
      <div class="tv-logo">📈 <span>KRX</span> 주식 스크리너</div>
      <div class="tv-date">📅 {date_disp} 기준 &nbsp;|&nbsp; 총 {len(stocks):,}개 종목</div>
    </div>
    """, unsafe_allow_html=True)

    # ── 필터 Row 1: 시장 / 우선스팩 / 우량주 ──
    mkt_col, excl_col, qual_col = st.columns([3, 1, 1])
    with mkt_col:
        market = st.radio("시장", ["전체","KOSPI","KOSDAQ"],
                           horizontal=True, label_visibility="collapsed")
    with excl_col:
        excl = st.checkbox("우선·스팩 제외")
    with qual_col:
        quality_mode = st.checkbox("🏆 우량주")
    sort_by = "시가총액"

    # ── 우량주 조건 패널 ──
    if quality_mode:
        st.markdown('<div class="quality-panel">', unsafe_allow_html=True)
        qa, qb, qc = st.columns([2, 2, 0.8])
        with qa:
            mktcap_range = st.slider("시가총액(억)", min_value=0, max_value=100_000_000,
                value=(0, 100_000_000), step=10_000, help="시가총액 범위 (억원)")
        with qb:
            tval_range = st.slider("거래대금(억/일)", min_value=0, max_value=100_000_000,
                value=(0, 100_000_000), step=10_000, help="일 거래대금 범위 (억원)")
        with qc:
            req_profit = st.checkbox("흑자(EPS>0)", value=True)
        qd, qe = st.columns([1, 1])
        with qd:
            div_range = st.slider("배당수익률(%)", min_value=0.0, max_value=15.0,
                value=(0.0, 15.0), step=0.5, help="배당수익률 범위 (%)")
        with qe:
            pbr_range = st.slider("PBR", min_value=0.0, max_value=30.0,
                value=(0.0, 30.0), step=0.5, help="PBR 범위 (없는 종목은 통과)")
        st.markdown('</div>', unsafe_allow_html=True)

        # DART 심화 필터 expander
        with st.expander("📊 DART 심화 필터 (ROE · 부채비율 · 영업이익률)"):
            da, db, dc, dd = st.columns(4)
            with da:
                min_roe = st.number_input("ROE 최소(%)", 0, 60, 0, 1)
            with db:
                max_debt = st.number_input("부채비율 최대(%)", 0, 999, 999, 50)
            with dc:
                min_op_margin = st.number_input("영업이익률 최소(%)", 0, 60, 0, 1)
            with dd:
                dart_load = st.button("🔍 DART 로드 & 적용",
                    help="필터된 종목의 DART 재무 데이터를 조회합니다 (최초 1~2분 소요)")
    # quality_mode=False 시 DART/KRX 필터 변수 미참조 (if quality_mode 가드)

    # ── 필터링 ──
    q = search.strip().lower()
    filtered = [s for s in stocks
        if (market == "전체" or s["market"] == market)
        and (not q or q in s["name"].lower() or q in s["code"])
        and (not excl or (not s["name"].endswith("우") and "스팩" not in s["name"]))
    ]

    # KRX 우량주 기본 필터
    if quality_mode:
        def _krx_ok(s):
            mc = (s.get("mktcap") or 0) / 1e8
            if not (mktcap_range[0] <= mc <= mktcap_range[1]):
                return False
            tv = (s.get("tval") or 0) / 1e8
            if not (tval_range[0] <= tv <= tval_range[1]):
                return False
            if req_profit and (s.get("eps") or 0) <= 0:
                return False
            div = s.get("div") or 0
            if div_range[0] > 0 and div < div_range[0]:
                return False
            if div_range[1] < 15.0 and div > div_range[1]:
                return False
            pbr = s.get("pbr")
            if pbr is not None:
                if pbr_range[0] > 0 and pbr < pbr_range[0]:
                    return False
                if pbr_range[1] < 30.0 and pbr > pbr_range[1]:
                    return False
            return True
        filtered = [s for s in filtered if _krx_ok(s)]

    filtered.sort(key=lambda x: x.get("mktcap", 0) or 0, reverse=True)

    # DART 심화 필터 처리
    dart_data = st.session_state.get("dart_data", {})
    if quality_mode and dart_load:
        if len(filtered) > 500:
            st.warning(f"⚠️ 현재 {len(filtered):,}개 종목은 DART 조회에 시간이 오래 걸립니다. "
                       "시가총액/거래대금 조건을 높여 500개 이하로 줄인 후 시도해 주세요.")
        else:
            codes_to_load = [s["code"] for s in filtered
                             if s["code"] not in dart_data]
            if codes_to_load:
                prog = st.progress(0, text=f"DART 재무 조회 중... 0/{len(codes_to_load)}")
                # code → stock 빠른 조회
                stock_lookup = {s["code"]: s for s in filtered}
                for i, code in enumerate(codes_to_load):
                    raw  = fetch_dart_financials(code)
                    stk  = stock_lookup.get(code, {})
                    dart_data[code] = get_quality_metrics(
                        raw,
                        close=stk.get("close", 0),
                        shares=stk.get("shares", 0),
                    )
                    prog.progress((i+1)/len(codes_to_load),
                                  text=f"DART 재무 조회 중... {i+1}/{len(codes_to_load)}")
                st.session_state["dart_data"] = dart_data
                prog.empty()
            else:
                st.toast("✅ DART 데이터 이미 로드됨")

    if quality_mode and dart_data and (min_roe > 0 or max_debt < 999 or min_op_margin > 0):
        def _dart_ok(s):
            m = dart_data.get(s["code"], {})
            if not m:
                return True  # 데이터 없는 종목은 통과
            if min_roe > 0 and m.get("roe", 0) < min_roe:
                return False
            if max_debt < 999 and m.get("debt_ratio", 0) > max_debt:
                return False
            if min_op_margin > 0 and m.get("op_margin", 0) < min_op_margin:
                return False
            return True
        filtered = [s for s in filtered if _dart_ok(s)]

    # ── 위로가기 버튼: 테이블 위 iframe 버튼 (항상 보임) + 체크박스 숨기기 ──
    _scroll_btn = """
    <style>
      body{margin:0;background:transparent;}
      #gtb{
        display:flex;align-items:center;gap:6px;
        padding:5px 14px;border:none;border-radius:20px;cursor:pointer;
        background:rgba(26,111,232,.85);color:#fff;font-size:13px;font-weight:600;
        box-shadow:0 2px 8px rgba(0,0,0,.18);white-space:nowrap;
      }
      #gtb:hover{background:rgba(20,88,192,.9);}
    </style>
    <script>
    function goTop(){
      var pd=window.parent.document;
      /* 1) 데이터프레임 내부 스크롤러 찾기 */
      var df=pd.querySelector('div[data-testid="stDataFrame"]');
      if(df){
        var all=df.querySelectorAll('*');
        for(var i=0;i<all.length;i++){
          var el=all[i];
          var st=window.parent.getComputedStyle(el);
          var ov=st.overflow+' '+st.overflowY;
          if((ov.indexOf('auto')>=0||ov.indexOf('scroll')>=0)&&el.scrollTop>0){
            el.scrollTop=0;
          }
        }
        /* canvas 기반 그리드: scrollTop 리셋 후 포커스 이벤트로 강제 갱신 */
        var canvas=df.querySelector('canvas');
        if(canvas){ canvas.dispatchEvent(new Event('scroll')); }
      }
      /* 2) 페이지 자체도 최상단으로 */
      var pageTargets=['section[data-testid="stMain"]',
                       'div[data-testid="stMainBlockContainer"]',
                       'section.main','.main'];
      for(var j=0;j<pageTargets.length;j++){
        var pel=pd.querySelector(pageTargets[j]);
        if(pel&&pel.scrollHeight>pel.clientHeight){
          pel.scrollTo({top:0,behavior:"smooth"});break;
        }
      }
      window.parent.scrollTo({top:0,behavior:"smooth"});
    }
    </script>
    <button id="gtb" onclick="goTop()">&#9650; 맨 위로</button>
    """
    _cb_hide = """
    <script>
    (function(){
      var p=window.parent;
      function hideCB(){
        p.document.querySelectorAll(
          'div[data-testid="stDataFrame"] input[type="checkbox"]'
        ).forEach(function(el){
          el.style.display='none';
          if(el.parentElement) el.parentElement.style.cssText+=
            'width:0!important;min-width:0!important;padding:0!important;overflow:hidden!important;';
        });
        p.document.querySelectorAll(
          'div[data-testid="stDataFrame"] [aria-colindex="1"]'
        ).forEach(function(el){
          el.style.cssText+='width:0!important;min-width:0!important;'
            +'padding:0!important;overflow:hidden!important;border:none!important;';
        });
      }
      function centerCells(){
        p.document.querySelectorAll(
          'div[data-testid="stDataFrame"] [role="columnheader"],'
          +'div[data-testid="stDataFrame"] [role="gridcell"]'
        ).forEach(function(el){
          el.style.justifyContent='center';
          el.style.textAlign='center';
          el.style.alignItems='center';
          el.style.display='flex';
        });

      }
      hideCB(); centerCells();
      var df=p.document.querySelector('div[data-testid="stDataFrame"]');
      if(df&&!df._cbo){
        df._cbo=new MutationObserver(function(){hideCB();centerCells();});
        df._cbo.observe(df,{subtree:true,childList:true});
      }
    })();
    </script>
    """
    col_count, col_dart_btn, col_btn = st.columns([5, 1, 1])
    with col_count:
        st.markdown(f'<div class="tv-count" style="padding-top:6px">🔎 {len(filtered):,}개 종목 표시</div>',
                    unsafe_allow_html=True)
    with col_dart_btn:
        main_dart_load = st.button("📊 재무 로드",
            help="표시 종목의 DART 재무 데이터(영업이익·배당금) 조회")
    with col_btn:
        st.components.v1.html(_scroll_btn, height=36)
    st.components.v1.html(_cb_hide, height=0)

    # 메인 뷰 DART 로드
    if main_dart_load:
        codes_to_load = [s["code"] for s in filtered if s["code"] not in dart_data]
        if len(filtered) > 500:
            st.warning(f"⚠️ {len(filtered):,}개는 너무 많습니다. 필터로 500개 이하로 줄여주세요.")
        elif codes_to_load:
            prog = st.progress(0, text=f"DART 조회 중... 0/{len(codes_to_load)}")
            stock_lookup = {s["code"]: s for s in filtered}
            for i, code in enumerate(codes_to_load):
                raw  = fetch_dart_financials(code)
                stk  = stock_lookup.get(code, {})
                dart_data[code] = get_quality_metrics(
                    raw, close=stk.get("close", 0), shares=stk.get("shares", 0))
                prog.progress((i+1)/len(codes_to_load),
                    text=f"DART 조회 중... {i+1}/{len(codes_to_load)}")
            st.session_state["dart_data"] = dart_data
            prog.empty()
        else:
            st.toast("✅ 이미 로드됨")

    # ── 종목 테이블 ──
    if not filtered:
        st.info("조건에 맞는 종목이 없습니다.")
        return

    def _quality_score(s):
        """조건 충족 개수 계산"""
        score = 0
        if (s.get("mktcap") or 0) >= 3e11:           score += 1
        if (s.get("tval")   or 0) >= 1e9:             score += 1
        if (s.get("eps")    or 0) >  0:               score += 1
        if (s.get("div")    or 0) >= 1.0:             score += 1
        pbr = s.get("pbr")
        if pbr and 0 < pbr <= 3:                      score += 1
        dm = dart_data.get(s["code"], {})
        if dm.get("roe",       0) >= 8:               score += 1
        if dm.get("debt_ratio",999) <= 200:           score += 1
        if dm.get("op_margin", 0) >= 5:               score += 1
        return score

    MAX_SCORE = 8

    rows_data = []
    for s in filtered:
        row = {
            "종목명":    s["name"],
            "시장":      s["market"],
            "현재가(원)": int(s["close"]) if s["close"] else 0,
            "등락률(%)": round(s["chg_rt"], 2) if s["chg_rt"] else 0.0,
            "거래대금(억)": round(s["tval"] / 1e8, 1) if s.get("tval") else
                           round(s["close"] * s["volume"] / 1e8, 1) if s["close"] and s["volume"] else 0.0,
            "거래량(주)": int(s["volume"]) if s["volume"] else 0,
            "시가총액(억)": fmt_mktcap_eok(s["mktcap"]) if s.get("mktcap") else 0,
            "주식수(주)":   int(s["shares"]) if s.get("shares") else None,
            "영업이익(억)": dart_data.get(s["code"], {}).get("op_income_eok"),
            "배당금(억)":   dart_data.get(s["code"], {}).get("dividends_eok"),
            "EPS(원)":      int(s["eps"]) if s.get("eps") else None,
        }
        if quality_mode:
            dm_tmp = dart_data.get(s["code"], {})
            # PBR: KRX 직접값 우선, 없으면 DART 계산값
            pbr_val = s.get("pbr") or dm_tmp.get("pbr_dart")
            row["PBR"]    = round(pbr_val, 2) if pbr_val else None
            # DIV: KRX 직접값 우선, 없으면 DART 계산값
            div_val = (s.get("div") or 0) or dm_tmp.get("div_dart")
            row["DIV(%)"] = round(div_val, 2) if div_val else None
            dm = dart_data.get(s["code"], {})
            if dm:
                row["ROE(%)"]  = dm.get("roe")
                row["부채비율(%)"] = dm.get("debt_ratio")
            sc = _quality_score(s)
            row["점수"] = sc
        rows_data.append(row)

    df = pd.DataFrame(rows_data)

    col_cfg = {
        "등락률(%)":    st.column_config.NumberColumn(format="%.2f%%"),
        "현재가(원)":   st.column_config.NumberColumn(format="%,d"),
        "거래대금(억)": st.column_config.NumberColumn(format="%,.1f억"),
        "거래량(주)":   st.column_config.NumberColumn(format="%,d"),
        "시가총액(억)": st.column_config.NumberColumn(format="%,d억"),
        "주식수(주)":   st.column_config.NumberColumn(format="%,d"),
        "영업이익(억)": st.column_config.NumberColumn(format="%,d억"),
        "배당금(억)":   st.column_config.NumberColumn(format="%,d억"),
        "EPS(원)":      st.column_config.NumberColumn(format="%,d"),
    }
    if quality_mode:
        col_cfg["PBR"]      = st.column_config.NumberColumn(format="%.2f")
        col_cfg["DIV(%)"]   = st.column_config.NumberColumn(format="%.1f%%")
        col_cfg["ROE(%)"]   = st.column_config.NumberColumn(format="%.1f%%")
        col_cfg["부채비율(%)"] = st.column_config.NumberColumn(format="%.0f%%")
        col_cfg["점수"] = st.column_config.ProgressColumn(
            "우량점수", min_value=0, max_value=MAX_SCORE, format="%d")

    event = st.dataframe(
        df, use_container_width=True, hide_index=True,
        height=600,
        on_select="rerun", selection_mode="single-row",
        column_config=col_cfg,
    )

    rows = event.selection.rows if hasattr(event, "selection") else []
    if rows:
        selected_stock = filtered[rows[0]]
        st.session_state["selected"] = selected_stock
        st.rerun()

main()
