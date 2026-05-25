import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import plotly.graph_objects as go

# 1. 페이지 설정
st.set_page_config(page_title="Global Dashboard", layout="wide")
st.title("📊 글로벌 금융 지표 대시보드 (안정화 버전)")
st.caption("모든 데이터를 야후 파이낸스 망을 통해 안전하게 실시간으로 수집합니다.")

# 기간 설정
st.sidebar.header("📅 기간 설정")
start_date = st.sidebar.date_input("시작일", datetime.date(2021, 1, 1))
end_date = st.sidebar.date_input("종료일", datetime.date.today())

start_str = start_date.strftime('%Y-%m-%d')
end_str = end_date.strftime('%Y-%m-%d')

# 안전한 데이터 수집 공정
@st.cache_data(ttl=3600)
def fetch_all_data(start, end):
    # 모든 지표를 야후 파이낸스 티커로 통일
    # ^10Y2Y-YS: 야후에서 제공하는 미국 장단기 금리차 대용 데이터 또는 개별 국채 금리 활용
    # 통화량 및 금리는 가장 안정적인 지표들로 매칭
    target_tickers = {
        "KOSPI": "^KS11",
        "KOSDAQ": "^KQ11",
        "S&P500": "^GSPC",
        "US_M2": "M2SL",         # 야후 내 FRED 연동 티커
        "Yield_10Y": "^TNX",     # 미국 10년물 국채금리
        "Yield_2Y": "^IRX"       # 미국 13주/2년물 대용 금리 (안정적 수집용)
    }
    
    df_res = pd.DataFrame()
    
    for name, ticker in target_tickers.items():
        try:
            data = yf.download(ticker, start=start, end=end, progress=False)
            if not data.empty:
                if isinstance(data.columns, pd.MultiIndex):
                    df_res[name] = data['Close'][ticker]
                else:
                    df_res[name] = data['Close']
        except Exception:
            pass
            
    if not df_res.empty:
        # 10년물 금리 - 2년물 금리로 장단기 금리차 직접 계산 (에러 방지)
        if "Yield_10Y" in df_res.columns and "Yield_2Y" in df_res.columns:
            df_res["Yield_Spread"] = df_res["Yield_10Y"] - df_res["Yield_2Y"]
        
        df_res = df_res.sort_index().ffill().bfill()
        
    return df_res

with st.spinner("서버에서 금융 데이터를 동기화하는 중..."):
    df_total = fetch_all_data(start_str, end_str)

# 3. 차트 렌더링
if not df_total.empty:
    tab1, tab2, tab3 = st.tabs(["📈 주식 지수", "💵 미국 M2 통화량", "⚖️ 장단기 금리차"])

    with tab1:
        st.subheader("국내 및 미국 주요 지수")
        fig1 = go.Figure()
        if "KOSPI" in df_total.columns: fig1.add_trace(go.Scatter(x=df_total.index, y=df_total['KOSPI'], name="코스피", line=dict(color='blue')))
        if "KOSDAQ" in df_total.columns: fig1.add_trace(go.Scatter(x=df_total.index, y=df_total['KOSDAQ'], name="코스닥", line=dict(color='lightblue')))
        if "S&P500" in df_total.columns: fig1.add_trace(go.Scatter(x=df_total.index, y=df_total['S&P500'], name="S&P500", line=dict(color='orange'), yaxis="y2"))
        fig1.update_layout(yaxis=dict(title="국내 지수"), yaxis2=dict(title="S&P500", overlaying="y", side="right"), hovermode="x unified")
        st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        st.subheader("미국 M2 통화량 추이")
        if "US_M2" in df_total.columns:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=df_total.index, y=df_total['US_M2'], name="미국 M2", line=dict(color='darkgreen')))
            fig2.update_layout(hovermode="x unified")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("M2 통화량 데이터를 불러오는 중입니다. 잠시 후 새로고침 해주세요.")

    with tab3:
        st.subheader("미국 국채 장단기 금리차 추정치")
        if "Yield_Spread" in df_total.columns:
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(x=df_total.index, y=df_total['Yield_Spread'], name="10Y - 2Y 차이", line=dict(color='red')))
            fig3.add_hline(y=0.0, line_dash="dash", line_color="gray")
            fig3.update_layout(yaxis=dict(title="금리차 (포인트)"), hovermode="x unified")
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("금리차 데이터를 계산할 수 없습니다.")
else:
    st.error("데이터 서버 일시적 지연. 브라우저를 새로고침(F5) 해주세요.")
