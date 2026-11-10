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

# 動態搜尋南昌站的 Stop ID
@st.cache_data(ttl=3600)  # 快取 1 小時，避免頻繁請求
def get_nam_cheong_stops():
    route = "20"
    target_keyword = "南昌站"
    directions = ["outbound", "inbound"]
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
        current_time = datetime.now()
        st.markdown(f"⏱️ **最後更新時間:** `{current_time.strftime('%Y-%m-%d %H:%M:%S')}` *(每 30 秒自動更新)*")
        
        for s in stops:
            stop_id = s['stop_id']
            stop_name = s['name_tc']
            direction = s['direction']
            
            st.subheader(f"📍 站點: {stop_name}")
            st.caption(f"方向: {direction.upper()} | Stop ID: `{stop_id}`")
            
            eta_url = f"https://rt.data.gov.hk/v2/transport/citybus/eta/CTB/{stop_id}/20"
            res = requests.get(eta_url)
            
            if res.status_code == 200:
                eta_data = res.json().get("data", [])
                
                if not eta_data:
                    st.info("目前此站點暫無實時到站班次資料（可能該時段暫無班次）。")
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
                st.warning("無法取得該站點的 ETA 資料。")

    render_eta()

    if st.button("🔄 立即手動重新整理"):
        st.rerun()
