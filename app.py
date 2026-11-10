import streamlit as st
import requests
from datetime import datetime, timezone, timedelta

# ==================== 用戶自訂設定區 ====================
CUSTOM_TITLE = "🚍 城巴 20 號線（南昌站）實時到站"  # <-- 可以在這裡隨時更改你的網頁標題
FONT_SIZE = "10px"                                      # <-- 可以在這裡更改表格與內容文字的大小 (例如 16px, 18px, 20px)
# ========================================================

# 定義香港時區 (UTC+8)
HK_TZ = timezone(timedelta(hours=8))

st.set_page_config(
    page_title=CUSTOM_TITLE,
    page_icon="🚍",
    layout="centered"
)

# 顯示標題
st.title(CUSTOM_TITLE)
st.markdown(f"<span style='font-size: {FONT_SIZE};'>即時顯示城巴 20 號線在南昌站的最新到站預報（每 30 秒自動更新）。</span>", unsafe_allow_html=True)

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
        now_hk = datetime.now(HK_TZ)
        st.markdown(f"<span style='font-size: {FONT_SIZE};'>⏱️ <b>最後更新時間:</b> {now_hk.strftime('%Y-%m-%d %H:%M:%S')} <i>(每 30 秒自動更新)</i></span>", unsafe_allow_html=True)
        
        for s in stops:
            stop_id = s['stop_id']
            stop_name = s['name_tc']
            direction = s['direction']
            
            st.markdown(f"### 📍 站點: {stop_name}")
            st.markdown(f"<span style='font-size: 14px; color: gray;'>方向: {direction.upper()} | Stop ID: {stop_id}</span>", unsafe_allow_html=True)
            
            eta_url = f"https://rt.data.gov.hk/v2/transport/citybus/eta/CTB/{stop_id}/20"
            res = requests.get(eta_url)
            
            if res.status_code == 200:
                eta_data = res.json().get("data", [])
                
                if not eta_data:
                    st.info("目前此站點暫無實時到站班次資料（可能該時段暫無班次）。")
                    continue
                
                # 組合 HTML 表格以便精準控制文字大小
                table_html = f"""
                <table style="width:100%; font-size: {FONT_SIZE}; border-collapse: collapse;">
                  <tr style="border-bottom: 1px solid #ddd; text-align: left;">
                    <th style="padding: 8px;">班次</th>
                    <th style="padding: 8px;">目的地</th>
                    <th style="padding: 8px;">預計到站</th>
                  </tr>
                """
                
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
                        
                    table_html += f"""
                      <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 8px;">第 {i} 架</td>
                        <td style="padding: 8px;">{dest}</td>
                        <td style="padding: 8px;">{time_desc}</td>
                      </tr>
                    """
                
                table_html += "</table>"
                st.markdown(table_html, unsafe_allow_html=True)
                
            else:
                st.warning("無法取得該站點的 ETA 資料。")

    render_eta()

    if st.button("🔄 立即手動重新整理"):
        st.rerun()
