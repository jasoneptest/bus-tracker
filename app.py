import streamlit as st
import requests
from datetime import datetime, timezone, timedelta

# ==================== 設定區 ====================
CUSTOM_TITLE = "城巴 20 號線（南昌站）實時到站"
TITLE_SIZE = "28px"
CONTENT_SIZE = "18px"     # 一般說明文字大小
TABLE_TEXT_SIZE = "20px"  # 📌 表格內的文字大小（可在此自由更改，例如 16px、18px）
STATION_SIZE = "22px"     # 站點名稱大小
# ==================================================

HK_TZ = timezone(timedelta(hours=8))

st.set_page_config(
    page_title=CUSTOM_TITLE,
    page_icon="🚍",
    layout="centered"
)

# 透過 CSS 樣式控制表格內的文字大小
st.markdown(f"""
    <style>
    table {{
        font-size: {TABLE_TEXT_SIZE} !important;
    }}
    </style>
""", unsafe_allow_html=True)

st.markdown(f"<h1 style='font-size: {TITLE_SIZE};'>{CUSTOM_TITLE}</h1>", unsafe_allow_html=True)
#st.markdown(f"<span style='font-size: {CONTENT_SIZE};'>即時顯示城巴 20 號線在南昌站的最新到站預報（每 30 秒自動更新）。</span>", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def get_nam_cheong_stops():
    route = "20"
    target_keyword = "南昌站"
    # 📌 將 inbound (往啟德) 放前面，讓它排在上面；outbound (往海達邨) 放後面
    directions = ["inbound", "outbound"]
    found_stops = []
    
    for direction in directions:
        route_stop_url = f"https://rt.data.gov.hk/v2/transport/citybus/route-stop/CTB/{route}/{direction}"
        res = requests.get(route_stop_url)
        if res.status_code != 200:
            continue
            
        for item in res.json().get("data", []):
            stop_id = item.get("stop")
            stop_res = requests.get(f"https://rt.data.gov.hk/v2/transport/citybus/stop/{stop_id}")
            if stop_res.status_code == 200:
                name_tc = stop_res.json().get("data", {}).get("name_tc", "")
                if target_keyword in name_tc:
                    if not any(s['stop_id'] == stop_id for s in found_stops):
                        found_stops.append({
                            "stop_id": stop_id,
                            "name_tc": name_tc,
                            "direction": direction
                        })
    return found_stops

stops = get_nam_cheong_stops()

if not stops:
    st.error("❌ 找不到城巴 20 號線途經的南昌站站點資料，請檢查網路或稍後再試。")
else:
    @st.fragment(run_every=30)
    def render_eta():
        now_hk = datetime.now(HK_TZ)
        st.markdown(f"<br><span style='font-size: {CONTENT_SIZE};'>⏱️ <b>最後更新時間:</b> {now_hk.strftime('%Y-%m-%d %H:%M:%S')} <i>(每 30 秒自動更新)</i></span>", unsafe_allow_html=True)
        
        for s in stops:
            stop_id = s['stop_id']
            stop_name = s['name_tc']
            direction = s['direction']
            
            # 根據方向自訂顯示名稱
            if direction == "outbound":
                display_station_name = "南昌站往海達邨"
            else:
                display_station_name = "南昌站往啟德"
            
            st.markdown(f"<div style='margin-top: 20px; font-size: {STATION_SIZE}; font-weight: bold;'>📍 站點: {display_station_name}</div>", unsafe_allow_html=True)
            #st.markdown(f"<span style='font-size: 14px; color: gray;'>方向: {direction.upper()} | Stop ID: {stop_id}</span>", unsafe_allow_html=True)
            
            eta_url = f"https://rt.data.gov.hk/v2/transport/citybus/eta/CTB/{stop_id}/20"
            res = requests.get(eta_url)
            
            if res.status_code == 200:
                eta_data = res.json().get("data", [])
                
                if not eta_data:
                    st.info("目前此站點暫無實時到站班次資料（可能該時段暫無班次）。")
                    continue
                
                table_data = []
                for i, item in enumerate(eta_data, 1):
                    dest = item.get("dest_tc", "")
                    eta_str = item.get("eta")
                    
                    if eta_str:
                        eta_dt = datetime.fromisoformat(eta_str).astimezone(HK_TZ)
                        eta_time_str = eta_dt.strftime('%H:%M:%S')
                        diff_seconds = (eta_dt - now_hk).total_seconds()
                        diff_mins = max(0, int(round(diff_seconds / 60)))
                        
                        if diff_mins <= 0:
                            time_desc = f"即將到站 ({eta_time_str})"
                        else:
                            time_desc = f"約 {diff_mins} 分鐘後 ({eta_time_str})"
                    else:
                        time_desc = "暫無具體時間"
                        
                    table_data.append({
                        "班次": f"第 {i} 架",
                        "目的地": dest,
                        "預計到站": time_desc
                    })
                
                st.table(table_data)
                
            else:
                st.warning("無法取得該站點的 ETA 資料。")

    render_eta()

    if st.button("🔄 立即手動重新整理"):
        st.rerun()
