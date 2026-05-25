import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import plotly.graph_objects as go

# 1. 페이지 설정
st.set_page_config(page_title="Global Dashboard", layout="wide")
st.title("📊 글로벌 금융 지표 대시보드 (나스닥 추가 버전)")
st.caption("모든 지표를 야후 파이낸스 망을 통해 안전하게 실시간 수집합니다. 차트 상단의 기간 버튼을 이용해 보세요.")

# 기간 설정 (기본 시작일 2015년)
st.sidebar.header("📅 데이터 수집 기간")
start_date = st.sidebar.date_input("수집 시작일", datetime.date(2015, 1, 1))
end_date = st.sidebar.date_input("수집 종료일", datetime.date.today())

start_str = start_date.strftime('%Y-%m-%d')
end_str = end_date.strftime('%Y-%m-%d')

# 안전한 데이터 수집 공정
@st.cache_data(ttl=3600)
def fetch_all_data(start, end):
    # 나스닥 종합지수 (^IXIC) 티커 추가
    target_tickers = {
        "KOSPI": "^KS11",
        "KOSDAQ": "^KQ11",
        "S&P500": "^GSPC",
        "NASDAQ": "^IXIC",      # 👈 나스닥 추가
        "US_M2": "M2SL",         
        "Yield_10Y": "^TNX",     
        "Yield_2Y": "^IRX"       
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
        if "Yield_10Y" in df_res.columns and "Yield_2Y" in df_res.columns:
            df_res["Yield_Spread"] = df_res["Yield_10Y"] - df_res["Yield_2Y"]
        df_res = df_res.sort_index().ffill().bfill()
        
    return df_res

with st.spinner("서버에서 금융 데이터를 동기화하는 중..."):
    df_total = fetch_all_data(start_str, end_str)

# Plotly 금융 차트 전용 기간 버튼 공통 설정
range_buttons = dict(
    buttons=list([
        dict(count=1, label="1M", step="month", stepmode="backward"),
        dict(count=3, label="3M", step="month", stepmode="backward"),
        dict(count=6, label="6M", step="month", stepmode="backward"),
        dict(count=1, label="1Y", step="year", stepmode="backward"),
        dict(count=5, label="5Y", step="year", stepmode="backward"),
        dict(count=10, label="10Y", step="year", stepmode="backward"),
        dict(step="all", label="ALL")
    ]),
    bgcolor="rgba(150, 200, 250, 0.2)",
    activecolor="rgba(150, 200, 250, 0.6)",
    direction="left"
)

# 3. 차트 렌더링
if not df_total.empty:
    tab1, tab2, tab3 = st.tabs(["📈 주식 지수", "💵 미국 M2 통화량", "⚖️ 장단기 금리차"])

    with tab1:
        st.subheader("국내 및 미국 주요 지수 (나스닥 포함)")
        fig1 = go.Figure()
        
        # 국내 지수 (좌측 y축)
        if "KOSPI" in df_total.columns: fig1.add_trace(go.Scatter(x=df_total.index, y=df_total['KOSPI'], name="코스피", line=dict(color='blue')))
        if "KOSDAQ" in df_total.columns: fig1.add_trace(go.Scatter(x=df_total.index, y=df_total['KOSDAQ'], name="코스닥", line=dict(color='lightblue')))
        
        # 미국 지수 (우측 y축 - yaxis="y2")
        if "S&P500" in df_total.columns: fig1.add_trace(go.Scatter(x=df_total.index, y=df_total['S&P500'], name="S&P500", line=dict(color='orange'), yaxis="y2"))
        if "NASDAQ" in df_total.columns: fig1.add_trace(go.Scatter(x=df_total.index, y=df_total['NASDAQ'], name="나스닥", line=dict(color='darkred'), yaxis="y2")) # 👈 나스닥 선 추가
        
        fig1.update_layout(
            yaxis=dict(title="국내 지수 (포인트)"), 
            yaxis2=dict(title="미국 지수 (포인트)", overlaying="y", side="right"), 
            hovermode="x unified",
            xaxis=dict(rangeselector=range_buttons)
        )
        st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        st.subheader("미국 M2 통화량 추이")
        if "US_M2" in df_total.columns:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=df_total.index, y=df_total['US_M2'], name="미국 M2", line=dict(color='darkgreen')))
            fig2.update_layout(hovermode="x unified", xaxis=dict(rangeselector=range_buttons))
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("M2 통화량 데이터를 불러오는 중입니다.")

    with tab3:
        st.subheader("미국 국채 장단기 금리차 추정치")
        if "Yield_Spread" in df_total.columns:
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(x=df_total.index, y=df_total['Yield_Spread'], name="10Y - 2Y 차이", line=dict(color='red')))
            fig3.add_hline(y=0.0, line_dash="dash", line_color="gray")
            fig3.update_layout(yaxis=dict(title="금리차 (포인트)"), hovermode="x unified", xaxis=dict(rangeselector=range_buttons))
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("금리차 데이터를 계산할 수 없습니다.")
else:
    st.error("데이터 서버 지연. 브라우저를 새로고침(F5) 해주세요.")
