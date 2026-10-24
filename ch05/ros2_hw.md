# 第五章　課後作業：以 JSON 設定巡邏任務

## 作業目標

課堂上的 `patrol` 節點須在 RViz 以 Publish Point 逐一點選巡邏點。本作業改為事先將巡邏點與各點的任務寫在 JSON 檔中，由程式讀取後自動完成巡邏，並在每個巡邏點執行指定的任務（取料、卸貨），任務狀態以 ROS 2 主題發布。

---

## 一、準備檔案

```bash
cd ~/jetson-course && git pull
mkdir -p ~/hw5_<學號>
cp ~/jetson-course/ch05/tasks.json ~/hw5_<學號>/
```

| 檔案 | 說明 |
|---|---|
| `~/jetson-course/ch05/maps/map.yaml`、`map.pgm` | 本作業統一使用的地圖，請勿改用自己建立的地圖 |
| `~/jetson-course/ch05/tasks.json` | 範例 JSON；請複製到自己的資料夾後再修改 |
| `~/tb3_ws/src/tb3_course/tb3_course/patrol.py` | 課堂範例，可作為改寫的基礎 |

> **注意**
> - 同一組共用一台 Jetson 與同一個帳號。請將作業檔案放在自己的資料夾 `~/hw5_<學號>/`，不要修改其他同學或課程資料夾 `~/jetson-course` 內的檔案。
> - JSON 中的座標是相對於上述地圖的座標系。改用其他地圖時，同一組座標會對應到不同位置。

---

## 二、題目要求

### 基本要求

1. **讀取 JSON**：JSON 檔的路徑以參數 `waypoints_file` 傳入，不可寫死在程式中。
2. **設定初始位置**：讀取 JSON 中的 `initial_pose`，由程式設定車子的初始位置，取代 RViz 的 2D Pose Estimate。
3. **依序導航**：依 JSON 的順序前往各巡邏點，到達一點後再前往下一點；導航期間每 2 秒輸出一次剩餘距離。
4. **執行任務**：到達後依該點的 `task` 執行任務：
   - 於終端機輸出任務開始與完成的訊息，中間等待 `duration` 秒，模擬作業時間。
   - 將任務狀態發布至 `/task_status` 主題，訊息型別為 `std_msgs/msg/String`。
5. **記錄車上物品**：程式須記錄車上目前載有的物品。`pick` 時加入該物品；`place` 時移除該物品。若要卸下的物品不在車上，輸出警告並略過該任務。
6. **處理導航失敗**：巡邏點無法到達時，輸出原因並略過該點，繼續前往下一點，程式不可中止或停住。
7. **輸出摘要**：巡邏結束時輸出完成與失敗的點數，以及車上剩餘的物品。

---

## 三、JSON 格式

```json
{
  "initial_pose": {"x": 0.0, "y": 0.0, "yaw": 0.0},
  "loops": 1,
  "waypoints": [
    {"name": "料架A",  "x": -3.5, "y": 0.6,  "yaw": 0.0,  "task": "pick",  "item": "螺絲", "duration": 3},
    {"name": "料架B",  "x": -1.2, "y": 2.6,  "yaw": 1.57, "task": "pick",  "item": "墊片", "duration": 3},
    {"name": "組裝站", "x": 0.5,  "y": 1.6,  "yaw": 0.0,  "task": "place", "item": "螺絲", "duration": 5},
    {"name": "出貨區", "x": -1.9, "y": -1.5, "yaw": 3.14, "task": "place", "item": "齒輪", "duration": 2}
  ]
}
```

| 欄位 | 說明 |
|---|---|
| `initial_pose` | 車子在模擬啟動時於地圖中的位置與車頭方向；本作業的數值已經量測好，請勿修改 |
| `loops` | 巡邏圈數 |
| `name` | 巡邏點名稱，用於輸出訊息 |
| `x`、`y` | 巡邏點於地圖座標系的位置（公尺） |
| `yaw` | 到達時的車頭方向（弧度）；0 為 +x 方向，1.57 約為 90° |
| `task` | `pick`（取料）或 `place`（卸貨） |
| `item` | 物品名稱 |
| `duration` | 模擬作業時間（秒） |

範例中的「出貨區」要卸下車上沒有的「齒輪」，用來檢查基本要求第 5 點。

---

## 四、執行方式

本作業可透過遠端連線完成。在 MobaXterm 中開啟 4 個分頁，各分頁分別執行：

```bash
# 分頁 1：啟動模擬（不開 Gazebo 視窗）
ros2 launch turtlebot3_fortress turtlebot3_world.launch.py gui:=false

# 分頁 2：啟動 Nav2（不開 RViz），載入作業地圖
ros2 launch nav2_bringup bringup_launch.py use_sim_time:=True \
  map:=$HOME/jetson-course/ch05/maps/map.yaml \
  params_file:=/opt/ros/humble/share/turtlebot3_navigation2/param/humble/burger.yaml

# 分頁 3：執行自己的巡邏程式
cd ~/hw5_<學號>
python3 json_patrol.py --ros-args -p use_sim_time:=true \
  -p waypoints_file:=$HOME/hw5_<學號>/tasks.json

# 分頁 4：觀察任務狀態
ros2 topic echo /task_status
```

程式可以直接寫成一個 Python 檔，以 `python3` 執行，不必建立套件；若想建立成套件也可以，但請建在自己的工作空間（例如 `~/hw5_<學號>_ws`），不要放進共用的 `~/tb3_ws`。

> **注意**
> - 遠端連線時請勿開啟 Gazebo 或 RViz 視窗；經網路傳送畫面極慢，模擬速度會降至正常的一成以下。本作業以終端機輸出確認結果。
> - 同一台 Jetson 同一時間只能有一人執行模擬，否則彼此的主題會互相干擾。請組內協調使用時段。
> - 結束時在每個分頁按 Ctrl＋C。若下次啟動時模擬開不起來，先執行：`pkill -9 -f "ign gazebo"; pkill -9 -f ruby; ros2 daemon stop`

---

## 五、範例輸出

```text
[INFO] [basic_navigator]: 讀取 4 個巡邏點：/home/imilab/hw5_N12345678/tasks.json
[INFO] [basic_navigator]: Nav2 is ready for use!
[INFO] [basic_navigator]: 前往 料架A (-3.50, 0.60)
[INFO] [basic_navigator]:   剩餘距離 1.82 m
[INFO] [basic_navigator]: 抵達 料架A，開始取料：螺絲（3 秒）
[INFO] [basic_navigator]: 取料完成，車上物品：['螺絲']
...
[WARN] [basic_navigator]: 出貨區：車上沒有 齒輪，略過卸貨
[INFO] [basic_navigator]: 巡邏結束：完成 4 點，失敗 0 點；車上剩餘 ['墊片']
```

`ros2 topic echo /task_status` 的輸出（內容格式可自行設計）：

```text
data: 料架A：pick 螺絲 開始
---
data: 料架A：pick 螺絲 完成
---
```

---

## 六、繳交項目

| 項目 | 說明 |
|---|---|
| 程式碼 | `json_patrol.py` |
| JSON 檔 | 執行時所用的 `tasks.json` |
| 執行截圖 | 分頁 3 從開始到摘要的完整輸出，以及分頁 4 的 `/task_status` 輸出 |
| 書面說明（半頁以內） | 說明程式如何記錄車上物品、如何處理導航失敗與物品不在車上的情況 |
| Demo 講解影片 | 說明並展示這份作業之操作流程與完成項目 |

## 七、評分標準

| 項目 | 比例 |
|---|---|
| 讀取 JSON 與參數、設定初始位置、依序導航 | 30% |
| 執行任務並發布 `/task_status` | 20% |
| 記錄車上物品與錯誤處理（導航失敗） | 25% |
| 摘要輸出與書面說明 | 10% |
| 程式可讀性（命名、註解） | 5% |
| Demo 影片講解清晰程度、完整性 | 10% |
