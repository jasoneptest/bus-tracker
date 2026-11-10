import streamlit as st
import requests
from datetime import datetime, timezone, timedelta

# 定義香港時區 (UTC+8)
HK_TZ = timezone(timedelta(hours=8))

st.set_page_config(
    page_title="城巴 20 號線（南昌站）實時到站",
    page_icon="🚍",
    layout="centered"
)

st.title("🚍 城巴 20 號線（南昌站）實時到站查詢")
st.write("即時顯示城巴 20 號線在南昌站的最新到站預報（每 30 秒自動更新）。")

# 動態搜尋南昌站的 Stop ID
@st.cache_data(ttl=3600)
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
        # 以香港時區取得當前精準時間
        now_hk = datetime.now(HK_TZ)
        st.markdown(f"⏱️ **最後更新時間:** `{now_hk.strftime('%Y-%m-%d %H:%M:%S')}` *(每 30 秒自動更新)*")
        
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
                    
                    if eta_str:
                        # 解析 API 時間並統一轉換至香港時區
                        eta_dt = datetime.fromisoformat(eta_str).astimezone(HK_TZ)
                        eta_time_str = eta_dt.strftime('%H:%M:%S')
                        
                        # 計算與現在的時間差（秒）
                        diff_seconds = (eta_dt - now_hk).total_seconds()
                        diff_mins = int(round(diff_seconds / 60))
                        
                        if diff_mins <= 0:
                            time_desc = f"即將到站 ({eta_time_str})"
                        else:
                            time_desc = f"約 {diff_mins} 分鐘後 ({eta_time_str})"
                    else:
                        time_desc = "暫無具體時間"
                        
                    table_rows.append({
                        "班次": f"第 {i} 架",
                        "目的地": dest,
                        "預計到站": time_desc
                    })
                
                st.table(table_rows)
            else:
                st.warning("無法取得該站點的 ETA 資料。")

    render_eta()

    if st.button("🔄 立即手動重新整理"):
        st.rerun()
