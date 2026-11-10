import streamlit as st
import requests
from datetime import datetime, timezone, timedelta

# ==================== 設定區 ====================
CUSTOM_TITLE = "Bethany 20號專線巴士🚍實時到站查詢"
TITLE_SIZE = "28px"
CONTENT_SIZE = "18px"     # 一般說明文字大小
TABLE_TEXT_SIZE = "16px"  # 📌 表格內的文字大小（可在此自由更改，例如 16px、18px）
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

@st.cache_data(ttl=3600)
def get_bus_stops():
    route = "20"
    # 設定要監控的目標：分別指定方向、搜尋關鍵字、顯示名稱與需要對照目標站
    targets = [
        {"direction": "inbound", "keyword": "南昌站", "display_name": "返學: 南昌站往啟德", "target_stop": "海富苑"},
        {"direction": "outbound", "keyword": "柏景灣", "display_name": "放學: 柏景灣往海達邨", "target_stop": "南昌站"}
    ]
    
    found_stops = []
    
    for t in targets:
        direction = t["direction"]
        keyword = t["keyword"]
        display_name = t["display_name"]
        target_stop_name = t["target_stop"]
        
        route_stop_url = f"https://rt.data.gov.hk/v2/transport/citybus/route-stop/CTB/{route}/{direction}"
        res = requests.get(route_stop_url)
        if res.status_code != 200:
            continue
            
        stops_list = res.json().get("data", [])
        main_stop_id = None
        target_stop_id = None
        
        for item in stops_list:
            s_id = item.get("stop")
            stop_res = requests.get(f"https://rt.data.gov.hk/v2/transport/citybus/stop/{s_id}")
            if stop_res.status_code == 200:
                name_tc = stop_res.json().get("data", {}).get("name_tc", "")
                if keyword in name_tc and not main_stop_id:
                    main_stop_id = s_id
                if target_stop_name in name_tc:
                    target_stop_id = s_id
                    
        if main_stop_id:
            found_stops.append({
                "stop_id": main_stop_id,
                "name_tc": keyword,
                "direction": direction,
                "display_name": display_name,
                "target_stop_id": target_stop_id,
                "target_stop_name": target_stop_name
            })
            
    return found_stops

stops = get_bus_stops()

if not stops:
    st.error("❌ 找不到相關站點資料，請檢查網路或稍後再試。")
else:
    @st.fragment(run_every=30)
    def render_eta():
        now_hk = datetime.now(HK_TZ)
        st.markdown(f"<br><span style='font-size: {CONTENT_SIZE};'>⏱️ <b>最後更新時間:</b> {now_hk.strftime('%Y-%m-%d %H:%M:%S')} <i>(每 30 秒自動更新)</i></span>", unsafe_allow_html=True)
        
        for s in stops:
            stop_id = s['stop_id']
            display_name = s['display_name']
            direction = s['direction']
            target_stop_id = s['target_stop_id']
            target_stop_name = s['target_stop_name']
            
            st.markdown(f"<div style='margin-top: 20px; font-size: {STATION_SIZE}; font-weight: bold;'>📍 {display_name}</div>", unsafe_allow_html=True)
            
            # 查詢主要站點 ETA
            eta_url = f"https://rt.data.gov.hk/v2/transport/citybus/eta/CTB/{stop_id}/20"
            res = requests.get(eta_url)
            
            # 查詢目標對照站的 ETA (例如海富苑 或 南昌站)
            target_eta_time = None
            if target_stop_id:
                target_eta_url = f"https://rt.data.gov.hk/v2/transport/citybus/eta/CTB/{target_stop_id}/20"
                target_res = requests.get(target_eta_url)
                if target_res.status_code == 200:
                    target_eta_data = target_res.json().get("data", [])
                    for t_item in target_eta_data:
                        t_eta_str = t_item.get("eta")
                        if t_eta_str:
                            t_dt = datetime.fromisoformat(t_eta_str).astimezone(HK_TZ)
                            diff_s = (t_dt - now_hk).total_seconds()
                            t_mins = max(0, int(round(diff_s / 60)))
                            target_eta_time = f"第一架車約 **{t_mins} 分鐘後** ({t_dt.strftime('%H:%M:%S')})"
                            break
            
            # 顯示目標站預計到達提示
            if target_eta_time:
                st.markdown(f"<div style='background-color: #f0f2f6; padding: 8px 12px; border-radius: 5px; margin-bottom: 8px; font-size: 15px;'>🚌 第一架車預計到達<b>{target_stop_name}</b>時間：{target_eta_time}</div>", unsafe_allow_html=True)
            
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
