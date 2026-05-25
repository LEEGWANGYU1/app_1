import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import plotly.graph_objects as go

# 1. 페이지 설정 및 초기화
st.set_page_config(page_title="Global Dashboard", layout="wide")
st.title("📊 글로벌 금융 지표 대시보드")
st.caption("M2 통화량, 국내외 증시, 장단기 금리차를 실시간으로 확인합니다.")

# 사이드바 기간 설정
st.sidebar.header("📅 기간 설정")
start_date = st.sidebar.date_input("시작일", datetime.date(2021, 1, 1))
end_date = st.sidebar.date_input("종료일", datetime.date.today())

# 날짜 포맷 변환
start_str = start_date.strftime('%Y-%m-%d')
end_str = end_date.strftime('%Y-%m-%d')

# 데이터 로딩 알림창 생성
status_text = st.empty()
status_text.info("🔄 데이터를 수집하는 중입니다. 잠시만 기다려주세요...")

df_total = pd.DataFrame()

try:
    # A. 야후 파이낸스에서 증시 지수 수집
    status_text.info("📈 1/2 단계: 국내 및 미국 주식 지수를 가져오는 중...")
    tickers = {"KOSPI": "^KS11", "KOSDAQ": "^KQ11", "S&P500": "^GSPC"}
    
    for name, ticker in tickers.items():
        data = yf.download(ticker, start=start_str, end=end_str, progress=False)
        if not data.empty:
            if isinstance(data.columns, pd.MultiIndex):
                df_total[name] = data['Close'][ticker]
            else:
                df_total[name] = data['Close']

    # B. FRED 경제 지표 수집 (에러 원천 차단 버전)
    status_text.info("💵 2/2 단계: 한/미 M2 통화량 및 금리차 데이터를 가져오는 중...")
    fred_tickers = {"US_M2": "M2SL", "KR_M2": "M2MSB156N", "Yield_Spread": "T10Y2Y"}
    
    for name, f_ticker in fred_tickers.items():
        fred_url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={f_ticker}"
        
        # [수정 포인트] parse_dates를 제거하고 일단 읽어온 뒤 날짜 컬럼을 유연하게 처리
        fred_df = pd.read_csv(fred_url)
        
        # 컬럼명을 모두 대문자로 통일하여 'DATE' 유실 문제 방지
        fred_df.columns = [col.upper() for col in fred_df.columns]
        
        if 'DATE' in fred_df.columns:
            fred_df['DATE'] = pd.to_datetime(fred_df['DATE'])
            fred_df.set_index('DATE', inplace=True)
            
            # 숫자가 아닌 값 처리 및 데이터 타입 변환
            fred_df[f_ticker] = pd.to_numeric(fred_df[f_ticker], errors='coerce')
            
            # 데이터 병합
            df_total[name] = fred_df[f_ticker]

    # C. 데이터 정제 (주말 및 공휴일 결측치 전방 복사)
    if not df_total.empty:
        df_total = df_total.sort_index().loc[start_str:end_str]
        df_total = df_total.ffill().bfill()
    
    # 상태 메시지 삭제
    status_text.empty()

except Exception as e:
    status_text.error(f"❌ 데이터 수집 중 치명적인 오류가 발생했습니다: {e}")
    df_total = pd.DataFrame()

# 3. 화면 UI 및 차트 렌더링 공정
if not df_total.empty:
    tab1, tab2, tab3 = st.tabs(["📈 주식 지수", "💵 한/미 M2 통화량", "⚖️ 장단기 금리차"])

    with tab1:
        st.subheader("국내 및 미국 주요 지수")
        fig1 = go.Figure()
        if "KOSPI" in df_total.columns: fig1.add_trace(go.Scatter(x=df_total.index, y=df_total['KOSPI'], name="코스피", line=dict(color='blue')))
        if "KOSDAQ" in df_total.columns: fig1.add_trace(go.Scatter(x=df_total.index, y=df_total['KOSDAQ'], name="코스닥", line=dict(color='lightblue')))
        if "S&P500" in df_total.columns: fig1.add_trace(go.Scatter(x=df_total.index, y=df_total['S&P500'], name="S&P500", line=dict(color='orange'), yaxis="y2"))
        
        fig1.update_layout(
            yaxis=dict(title="국내 지수"),
            yaxis2=dict(title="S&P500", overlaying="y", side="right"),
            hovermode="x unified", margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=1, xanchor="right")
        )
        st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        st.subheader("한·미 M2 통화량 비교 (시작일 = 100 기준 지수화)")
        if "US_M2" in df_total.columns and "KR_M2" in df_total.columns:
            df_m2 = df_total[['US_M2', 'KR_M2']].dropna()
            if not df_m2.empty:
                df_m2_norm = (df_m2 / df_m2.iloc) * 100
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(x=df_m2_norm.index, y=df_m2_norm['US_M2'], name="미국 M2", line=dict(color='darkgreen')))
                fig2.add_trace(go.Scatter(x=df_m2_norm.index, y=df_m2_norm['KR_M2'], name="한국 M2", line=dict(color='lightgreen')))
                fig2.update_layout(hovermode="x unified", margin=dict(l=20, r=20, t=30, b=20),
                                   legend=dict(orientation="h", yanchor="bottom", y=1.02, x=1, xanchor="right"))
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("M2 통화량 데이터를 표시할 수 없습니다.")

    with tab3:
        st.subheader("미국 국채 장단기 금리차 (10Y - 2Y)")
        if "Yield_Spread" in df_total.columns:
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(x=df_total.index, y=df_total['Yield_Spread'], name="10Y - 2Y", line=dict(color='red')))
            fig3.add_hline(y=0.0, line_dash="dash", line_color="gray")
            fig3.update_layout(yaxis=dict(title="금리차 (%)"), hovermode="x unified", margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("금리차 데이터를 표시할 수 없습니다.")
else:
    st.error("데이터프레임이 비어 있습니다. 인터넷 연결이나 깃허브 코드를 확인해 주세요.")
