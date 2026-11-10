import requests
import time
from datetime import datetime

def monitor_route_20_nam_cheong():
    route = "20"
    target_keyword = "南昌站"
    
    print(f"🔍 正在初始化：搜尋城巴 {route} 號線途經的「{target_keyword}」站點...\n")
    
    directions = ["outbound", "inbound"]
    found_stops = []
    
    # 1. 初始化時先找出南昌站的 Stop ID
    for direction in directions:
        route_stop_url = f"https://rt.data.gov.hk/v2/transport/citybus/route-stop/CTB/{route}/{direction}"
        res = requests.get(route_stop_url)
        
        if res.status_code != 200:
            continue
            
        stops_data = res.json().get("data", [])
        
        for item in stops_data:
            stop_id = item.get("stop")
            stop_detail_url = f"https://rt.data.gov.hk/v2/transport/citybus/stop/{stop_id}"
            stop_res = requests.get(stop_detail_url)
            
            if stop_res.status_code == 200:
                stop_info = stop_res.json().get("data", {})
                name_tc = stop_info.get("name_tc", "")
                
                if target_keyword in name_tc:
                    if not any(s['stop_id'] == stop_id for s in found_stops):
                        found_stops.append({
                            "stop_id": stop_id,
                            "name_tc": name_tc,
                            "direction": direction
                        })

    if not found_stops:
        print(f"❌ 找不到城巴 {route} 號線途經的「{target_keyword}」站點。")
        return

    print(f"✅ 成功鎖定站點，開始即時監控（每 30 秒自動更新一次，按 Ctrl+C 可隨時退出）：\n")
    for s in found_stops:
        print(f" - 站名: {s['name_tc']} | Stop ID: {s['stop_id']} | 方向: {s['direction']}")
    print("=" * 60)

    # 2. 進入 while 迴圈，定期抓取並顯示倒數時間
    try:
        while True:
            current_time = datetime.now()
            print(f"\n⏱️ 更新時間: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            for s in found_stops:
                stop_id = s['stop_id']
                stop_name = s['name_tc']
                
                eta_url = f"https://rt.data.gov.hk/v2/transport/citybus/eta/CTB/{stop_id}/{route}"
                eta_res = requests.get(eta_url)
                
                print(f"📍 站點: 【{stop_name}】 (ID: {stop_id})")
                
                if eta_res.status_code == 200:
                    eta_data = eta_res.json().get("data", [])
                    
                    if not eta_data:
                        print("   (目前暫無實時到站班次資料)")
                        continue
                    
                    for i, item in enumerate(eta_data, 1):
                        dest = item.get("dest_tc", "")
                        eta_str = item.get("eta")
                        rmk = item.get("rmk_tc", "")
                        
                        if eta_str:
                            eta_dt = datetime.fromisoformat(eta_str).replace(tzinfo=None)
                            eta_time_str = eta_dt.strftime('%H:%M:%S')
                            
                            # 計算距離現在還有幾分鐘
                            diff_seconds = (eta_dt - current_time).total_seconds()
                            diff_mins = max(0, int(round(diff_seconds / 60)))
                            
                            print(f"   [{i}] 往 {dest:<10} | 預計到站: {eta_time_str} (約 {diff_mins} 分鐘後) {f'[{rmk}]' if rmk else ''}")
                        else:
                            print(f"   [{i}] 往 {dest:<10} | 暫無具體時間 {f'[{rmk}]' if rmk else ''}")
                else:
                    print("   無法取得該站點的 ETA 資料。")
            
            print("-" * 60)
            print("⏳ 等待 30 秒後進行下一次更新...")
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\n👋 已手動停止即時監控程式。")

if __name__ == "__main__":
    monitor_route_20_nam_cheong()