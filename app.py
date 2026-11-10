import streamlit as st
import requests
from datetime import datetime

st.set_page_config(
    page_title="城巴 20 號線（南昌站）實時到站",
    page_icon="🚍",
    layout="centered"
)

st.title("🚍 城巴 20 號線（南昌站）實時到站查詢")
st.write("即時顯示城巴 20 號線在南昌站的最新到站預報（每 30 秒自動更新）。")

# 直接指定南昌站已知正確的 Stop ID，避免啟動時在雲端發送大量請求導致卡死
NAM_CHEONG_STOPS = [
    {
        "stop_id": "003347", 
        "name_tc": "南昌站 (深旺道)", 
        "direction": "outbound"
    }
]

@st.fragment(run_every=30)
def render_eta():
    current_time = datetime.now()
    st.markdown(f"⏱️ **最後更新時間:** `{current_time.strftime('%Y-%m-%d %H:%M:%S')}` *(每 30 秒自動更新)*")
    
    for s in NAM_CHEONG_STOPS:
        stop_id = s['stop_id']
        stop_name = s['name_tc']
        direction = s['direction']
        
        st.subheader(f"📍 站點: {stop_name}")
        st.caption(f"方向: {direction.upper()} | Stop ID: `{stop_id}`")
        
        eta_url = f"https://rt.data.gov.hk/v2/transport/citybus/eta/CTB/{stop_id}/20"
        
        try:
            res = requests.get(eta_url, timeout=5)
            if res.status_code == 200:
                eta_data = res.json().get("data", [])
                
                if not eta_data:
                    st.info("目前此站點暫無實時到站班次資料。")
                    continue
                
                table_rows = []
                for i, item in enumerate(eta_data, 1):
                    dest = item.get("dest_tc", "")
                    eta_str = item.get("eta")
                    rmk = item.get("rmk_tc", "")
                    
                    if eta_str:
                        eta_dt = datetime.fromisoformat(eta_str).replace(tzinfo=None)
                        eta_time_str = eta_dt.strftime('%H:%M:%S')
                        diff_seconds = (eta_dt - current_time).total_seconds()
                        diff_mins = max(0, int(round(diff_seconds / 60)))
                        time_desc = f"約 {diff_mins} 分鐘後 ({eta_time_str})"
                    else:
                        time_desc = "暫無具體時間"
                        
                    table_rows.append({
                        "班次": f"第 {i} 架",
                        "目的地": dest,
                        "預計到站": time_desc,
                        "備註": rmk if rmk else "-"
                    })
                
                st.table(table_rows)
            else:
                st.warning(f"無法取得 ETA 資料 (狀態碼: {res.status_code})")
        except Exception as e:
            st.error(f"連線發生錯誤: {e}")

# 加上載入提示
with st.spinner("正在取得最新巴士到站資訊..."):
    render_eta()

if st.button("🔄 立即手動重新整理"):
    st.rerun()
