# 第五章　ROS 2 安裝、模擬與範例指令整理（JetPack 6.2.2）

## 課程環境

本章全程於 Jetson Orin Nano 上完成。先安裝 ROS 2 Humble，以 turtlesim 認識 ROS 2 的核心概念；再以 Gazebo Fortress 模擬 TurtleBot3 Burger，撰寫節點並完成建圖與導航。

| 項目 | 內容 |
|---|---|
| 運算平台 | Jetson Orin Nano 開發者套件，JetPack 6.2.2（L4T 36.5，Ubuntu 22.04） |
| ROS 2 版本 | Humble（安裝於 `/opt/ros/humble`） |
| 模擬器 | Gazebo Fortress（指令為 `ign gazebo`） |
| 模擬機器人 | TurtleBot3 Burger（課程套件 `turtlebot3_fortress`） |
| 範例程式 | 課程套件 `tb3_course`：`obstacle_stop`、`drive_distance`、`patrol` |
| 工作空間 | `~/tb3_ws` |

> **注意**
> - Gazebo 與 RViz 須於 Jetson 所接的實體螢幕（本機桌面）執行；經 MobaXterm 遠端顯示時，模擬速度會降至正常的一成以下。
> - 終端機指令可經 MobaXterm 遠端執行，但開啟視窗的程式（Gazebo、RViz、rqt_graph、turtlesim）一律在本機桌面開啟。

| 節次 | 內容 | 使用環境 |
|---|---|---|
| 第一節 | ROS 簡介、ROS 與 ROS 2 的比較、安裝 ROS 2 Humble；核心概念：節點、主題、訊息、服務、參數、動作 | turtlesim |
| 第二節 | 安裝模擬環境、套件與工作空間、啟動檔；機器人模擬、光達、TF；撰寫第一個節點 `obstacle_stop` | TurtleBot3 模擬 |
| 第三節 | SLAM 建圖、Nav2 導航；以程式導航 `patrol` | TurtleBot3 模擬 |

---

## 5.1 ROS 簡介

ROS（Robot Operating System）並非作業系統，而是運行於 Linux 之上的機器人中介軟體：將機器人的感測、定位、規劃、控制等功能拆分為獨立執行的程式（節點），並提供節點之間交換資料的標準機制，以及開發工具與大量開源套件。

| 組成 | 說明 | 例 |
|---|---|---|
| 通訊機制 | 程式之間以主題、服務、動作等方式交換資料 | 本章 5.3 節 |
| 開發工具 | 指令列工具，以及資料視覺化與除錯工具 | `ros2` 指令、RViz、rqt |
| 功能套件 | 社群開發的現成功能，安裝後即可使用 | 建圖、導航、機械手臂控制 |
| 硬體驅動 | 常見感測器與機器人平台的驅動程式 | 光達、RealSense、TurtleBot3 |
| 模擬整合 | 與機器人模擬器連接，於電腦中測試程式 | Gazebo（本章第二節） |

## 5.1.1 從 ROS 到 ROS 2

| 項目 | ROS 1 | ROS 2 |
|---|---|---|
| 通訊架構 | 須執行 ROS Master（`roscore`）集中管理 | 無 Master，經 DDS 自動探索 |
| 通訊協定 | 自訂的 TCPROS／UDPROS | 工業標準 DDS，可設定 QoS |
| 即時控制 | 不支援 | 架構上支援 |
| 多機器人 | 須額外設定，較為困難 | 以 Domain ID 區隔，原生支援 |
| 安全性 | 無 | SROS2 提供加密與身分驗證 |
| 程式語言 | C++、Python（早期為 Python 2） | C++17、Python 3 |
| 編譯工具 | catkin | colcon |
| 作業系統 | 以 Ubuntu 為主 | Ubuntu、Windows、macOS |
| 維護狀態 | 最後版本 Noetic 於 2025 年 5 月停止維護 | 每年發布新版本 |

> **注意**
> - 本課程僅使用 ROS 2。網路教學中若出現 `roscore`、`rosrun`、`catkin_make` 等指令，即屬 ROS 1，無法於本課程的環境執行；ROS 2 的指令皆以 `ros2` 開頭。

## 5.1.2 ROS 2 的版本

ROS 2 每年 5 月發布新版本；偶數年發布者為長期支援版（LTS），維護 5 年。每個版本對應特定的 Ubuntu 版本。

| 版本 | 發布 | 停止維護 | Ubuntu | 類型 |
|---|---|---|---|---|
| Foxy Fitzroy | 2020 年 6 月 | 2023 年 6 月 | 20.04 | LTS（已停止） |
| **Humble Hawksbill** | 2022 年 5 月 | 2027 年 5 月 | 22.04 | LTS |
| Jazzy Jalisco | 2024 年 5 月 | 2029 年 5 月 | 24.04 | LTS |
| Kilted Kaiju | 2025 年 5 月 | 2026 年 12 月 | 24.04 | 一般版本 |
| Lyrical Luth | 2026 年 5 月 | 2031 年 5 月 | 26.04 | LTS |

JetPack 6.2.2 以 Ubuntu 22.04 為基礎，故本課程使用 **ROS 2 Humble**。

---

## 5.2 安裝 ROS 2 Humble

```bash
# 先確認是否已安裝：若顯示 humble，可直接由 5.2.3 開始
ls /opt/ros
```

| 步驟 | 內容 | 目的 |
|---|---|---|
| Step 1 | 確認系統語系（5.2.1） | ROS 2 的部分工具要求 UTF-8 編碼 |
| Step 2 | 加入 ROS 2 套件來源（5.2.1） | 使 apt 找得到 ROS 2 的套件 |
| Step 3 | 安裝 ROS 2 與開發工具（5.2.2） | 安裝 ROS 2 本體、圖形化工具與編譯工具 |
| Step 4 | 設定終端機環境（5.2.3） | 使終端機找得到 `ros2` 指令 |
| Step 5 | 執行範例程式（5.2.4） | 確認安裝與通訊正常 |

> **注意**
> - 安裝須連接網路，`ros-humble-desktop` 的下載量較大，須時較長。

## 5.2.1 設定語系與套件來源

```bash
# Step 1　確認系統語系（LANG 已為 UTF-8 者可略過）
locale
sudo apt update && sudo apt install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
locale                                     # 確認 LANG 已為 en_US.UTF-8

# Step 2　加入 ROS 2 套件來源
sudo apt update && sudo apt install -y software-properties-common curl
sudo add-apt-repository universe
V=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest \
    | grep -F "tag_name" | awk -F'"' '{print $4}')
C=$(. /etc/os-release && echo $VERSION_CODENAME)
echo $V $C                                 # 應顯示版本號與 jammy
U=https://github.com/ros-infrastructure/ros-apt-source/releases/download
curl -L -o /tmp/ros2-apt-source.deb $U/$V/ros2-apt-source_$V.${C}_all.deb
sudo dpkg -i /tmp/ros2-apt-source.deb
```

| 指令 | 說明 |
|---|---|
| `locale-gen` | 產生英文 UTF-8 語系資料 |
| `update-locale` | 將系統預設語系設為英文 UTF-8，重新登入後生效 |
| `export LANG=…` | 使目前的終端機立即套用新語系 |
| `add-apt-repository universe` | 啟用 Ubuntu 的 universe 套件庫，ROS 2 部分相依套件位於其中 |
| `V=…` | 自 GitHub 查詢 `ros2-apt-source` 的最新版本號 |
| `C=…` | 讀取 Ubuntu 的版本代號；Ubuntu 22.04 為 jammy |
| `curl`、`dpkg -i` | 下載對應版本的 `ros2-apt-source` 並安裝，自動完成套件庫與驗證金鑰的設定 |

## 5.2.2 安裝 ROS 2 套件

```bash
sudo apt update
sudo apt install -y ros-humble-desktop     # ROS 2 本體與圖形化工具
sudo apt install -y ros-dev-tools          # colcon 等開發工具
ls /opt/ros                                # 應顯示 humble
```

| 安裝組合 | 內容 | 本課程 |
|---|---|---|
| `ros-humble-ros-base` | 通訊函式庫、訊息定義與指令列工具，不含圖形介面；適用於無螢幕的機器人 | — |
| `ros-humble-desktop` | ros-base 加上 RViz、rqt、turtlesim 與範例程式 | 安裝 |
| `ros-dev-tools` | 編譯工具 colcon 與相關開發工具 | 安裝 |

> **注意**
> - ROS 2 安裝於 `/opt/ros/humble`；之後以 apt 安裝的 ROS 2 套件（名稱以 `ros-humble-` 開頭）亦位於此資料夾。

## 5.2.3 設定終端機環境

```bash
# 載入 ROS 2 環境，並寫入 ~/.bashrc（之後開啟的終端機自動載入）
source /opt/ros/humble/setup.bash
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc

# 限制通訊範圍於本機
echo "export ROS_LOCALHOST_ONLY=1" >> ~/.bashrc
source ~/.bashrc

# 確認
printenv | grep -E "ROS_DISTRO|ROS_LOCALHOST_ONLY"
```

**正常輸出**

```text
ROS_DISTRO=humble
ROS_LOCALHOST_ONLY=1
```

> **注意**
> - ROS 2 預設會自動探索同一網路上的所有節點。教室內多台 Jetson 連接相同網路時，若未設定 `ROS_LOCALHOST_ONLY=1`，甲同學的遙控指令可能驅動乙同學的機器人。

## 5.2.4 驗證安裝

```bash
ros2 run demo_nodes_cpp talker        # 終端機 1：每秒發布一則訊息（C++）
ros2 run demo_nodes_py listener       # 終端機 2：接收並顯示（Python）
```

**正常輸出**

```text
[INFO] [1760600000.123456789] [talker]: Publishing: 'Hello World: 1'
[INFO] [1760600001.125000000] [listener]: I heard: [Hello World: 1]
```

> **注意**
> - 結束 `talker` 後 `listener` 即停止輸出，重新啟動 `talker` 後隨即恢復；程式之間無須事先指定對方位址，由 DDS 自動探索。
> - `talker` 與 `listener` 即為 5.3 的「節點」，兩者交換資料的通道 `/chatter` 即為「主題」。

---

## 5.3 ROS 2 核心概念

turtlesim 已隨 `ros-humble-desktop` 安裝，不需另外安裝。

| 概念 | 說明 | 本節實作 |
|---|---|---|
| 節點（Node） | 執行單一功能的程式，為 ROS 2 系統的基本單元 | `turtlesim_node`、`turtle_teleop_key` |
| 主題（Topic） | 具名的資料通道，以發布／訂閱方式單向傳遞資料 | `/turtle1/cmd_vel` |
| 訊息（Message） | 主題上傳遞的資料格式 | `geometry_msgs/msg/Twist` |
| 服務（Service） | 請求／回應式的同步呼叫 | `/spawn`、`/clear` |
| 參數（Parameter） | 節點的設定值，可於執行中修改 | `background_r` |
| 動作（Action） | 耗時任務的非同步呼叫，具回饋並可中途取消 | `/turtle1/rotate_absolute` |

## 5.3.1 節點與主題

```bash
ros2 run turtlesim turtlesim_node        # 終端機 1：模擬器節點
ros2 run turtlesim turtle_teleop_key     # 終端機 2：鍵盤遙控節點（以方向鍵操作）

ros2 node list                           # 終端機 3：列出執行中的節點
ros2 topic list                          # 列出所有主題
rqt_graph                                # 節點關係圖
```

**`ros2 node list` 與 `ros2 topic list` 的正常輸出**

```text
/teleop_turtle
/turtlesim

/parameter_events
/rosout
/turtle1/cmd_vel
/turtle1/color_sensor
/turtle1/pose
```

| rqt_graph 圖示 | 意義 |
|---|---|
| 橢圓 | 節點 |
| 方框 | 主題 |
| 箭頭 | 資料流向：`/teleop_turtle` 發布 `/turtle1/cmd_vel`，由 `/turtlesim` 訂閱 |

> **注意**
> - 鍵盤遙控須讓終端機 2 保持在前景，按鍵才會被讀取。
> - rqt_graph 左上角選擇 `Nodes/Topics (all)`，再按重新整理。

## 5.3.2 訊息

```bash
# 查詢主題的訊息型別與欄位
ros2 topic info /turtle1/cmd_vel
ros2 interface show geometry_msgs/msg/Twist

# 讀取主題：烏龜的位置與方向
ros2 topic echo /turtle1/pose

# 發布主題：以指令讓烏龜畫圓（每秒發布一次）
ros2 topic pub --rate 1 /turtle1/cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 2.0}, angular: {z: 1.8}}"

# 量測主題的發布頻率
ros2 topic hz /turtle1/pose
```

| Twist 欄位 | 單位 | 用於平面移動機器人時的意義 |
|---|---|---|
| `linear.x` | 公尺／秒 | 前進（正值）或後退（負值）的速度 |
| `angular.z` | 弧度／秒 | 繞垂直軸旋轉的角速度，正值為逆時針 |
| 其餘欄位 | — | 不使用，維持 0 |

**練習**：分別改變 `linear.x` 與 `angular.z`，觀察圓的大小變化，並驗證圓的半徑等於 linear.x ÷ angular.z。

## 5.3.3 服務

```bash
ros2 service list                                     # 列出所有服務
ros2 service type /spawn                              # turtlesim/srv/Spawn
ros2 service call /spawn turtlesim/srv/Spawn \
  "{x: 2.0, y: 2.0, theta: 0.0, name: 'turtle2'}"     # 產生第二隻烏龜
ros2 service call /clear std_srvs/srv/Empty           # 清除軌跡
```

| 方式 | 通訊模式 | 適用情境 | turtlesim 範例 |
|---|---|---|---|
| 主題 | 發布／訂閱，持續單向傳送 | 感測資料、速度指令等連續資料 | `/turtle1/pose` |
| 服務 | 請求／回應，等待結果 | 一次性的查詢或設定 | `/spawn`、`/clear` |
| 動作 | 目標／回饋／結果，可取消 | 需時較長且須掌握進度的任務 | `rotate_absolute` |

## 5.3.4 參數

```bash
ros2 param list /turtlesim                        # 列出 turtlesim 的參數
ros2 param get /turtlesim background_r            # 讀取背景的紅色分量
ros2 param set /turtlesim background_r 150        # 修改後背景顏色立即改變
ros2 param dump /turtlesim > turtlesim.yaml       # 將目前參數存檔
ros2 run turtlesim turtlesim_node --ros-args --params-file turtlesim.yaml
```

| 參數 | 範圍 | 說明 |
|---|---|---|
| `background_r` | 0–255 | 背景的紅色分量 |
| `background_g` | 0–255 | 背景的綠色分量 |
| `background_b` | 0–255 | 背景的藍色分量 |

## 5.3.5 動作

```bash
ros2 action list -t
# /turtle1/rotate_absolute [turtlesim/action/RotateAbsolute]

ros2 action send_goal /turtle1/rotate_absolute turtlesim/action/RotateAbsolute \
  "{theta: 1.57}" --feedback      # 轉向 90°，並顯示回饋
```

| 階段 | 方向 | 例 |
|---|---|---|
| 目標（Goal） | 用戶端送出 | 轉到 90° |
| 回饋（Feedback） | 伺服器持續回傳 | 尚差幾度 |
| 結果（Result） | 任務結束時回傳 | 完成或取消 |

> **注意**
> - `turtle_teleop_key` 的 G、B、V、C、D、E、R、T 鍵亦是送出此動作；按 F 可取消。
> - 第三節的導航同樣以動作實現：目標為終點座標，回饋為剩餘距離，結果為是否到達。

---

## 5.4 機器人模擬器

本課程以 Gazebo Fortress 模擬 TurtleBot3 Burger。TurtleBot3 官方的 Humble 模擬套件使用 Gazebo Classic，無法安裝於 Jetson（arm64），故改用課程套件 `turtlebot3_fortress` 提供車子與場景。

> **注意**
> - 模擬速度不一定等於真實時間。ROS 2 節點須加上 `use_sim_time:=true`，改以 Gazebo 發布的 `/clock` 為時間基準。

## 5.4.1 安裝模擬器與相關套件

```bash
sudo apt update
sudo apt install -y ignition-fortress ros-humble-ros-gz \
  ros-humble-turtlebot3-teleop ros-humble-turtlebot3-cartographer \
  ros-humble-turtlebot3-navigation2 ros-humble-navigation2 \
  ros-humble-nav2-bringup ros-humble-nav2-simple-commander
```

| 套件 | 用途 |
|---|---|
| `ignition-fortress` | Gazebo Fortress 模擬器本體，負責物理與感測器運算 |
| `ros-humble-ros-gz` | Gazebo 與 ROS 2 的介面（ros_gz_bridge、ros_gz_sim） |
| `ros-humble-turtlebot3-teleop` | 鍵盤遙控節點 teleop_keyboard（5.4.5） |
| `ros-humble-turtlebot3-cartographer` | TurtleBot3 的建圖設定與啟動檔（5.6） |
| `ros-humble-turtlebot3-navigation2` | TurtleBot3 的導航參數與啟動檔（5.7） |
| `ros-humble-navigation2` | Nav2 導航系統本體（5.7） |
| `ros-humble-nav2-bringup` | Nav2 的標準啟動檔，供上述導航啟動檔呼叫 |
| `ros-humble-nav2-simple-commander` | Nav2 的 Python 介面，供 patrol 送出導航目標（5.7.1） |

## 5.4.2 套件與工作空間

```text
~/tb3_ws/                  # 工作空間
├── src/                   # 原始碼：所有套件皆置於此
│   ├── turtlebot3_fortress/
│   └── tb3_course/
├── build/                 # 編譯過程的中間檔
├── install/               # 編譯結果；setup.bash 位於此
└── log/                   # 編譯紀錄
```

| 建置類型 | 適用 | 主要檔案 | 本課程 |
|---|---|---|---|
| ament_python | 以 Python 撰寫的節點 | package.xml、setup.py | `tb3_course` |
| ament_cmake | 以 C++ 撰寫的節點，或僅含啟動檔、模型等資料 | package.xml、CMakeLists.txt | `turtlebot3_fortress` |

| 指令 | 說明 |
|---|---|
| `ros2 pkg list` | 列出目前找得到的所有套件 |
| `ros2 pkg prefix <套件>` | 顯示套件的安裝位置 |
| `ros2 pkg executables <套件>` | 列出套件內可用 `ros2 run` 執行的程式 |
| `ros2 pkg create --build-type ament_python <名稱>` | 於 src 內建立新套件的基本檔案 |

> **注意**
> - 系統的 ROS 2（`/opt/ros/humble`）與工作空間（`~/tb3_ws/install`）依序載入、層層疊加；工作空間須於系統的 ROS 2 之後載入。

## 5.4.3 取得並編譯課程套件

```bash
# Step 1　更新課程資料夾，將兩個套件複製到工作空間並編譯
cd ~/jetson-course && git pull
mkdir -p ~/tb3_ws/src
cp -r ~/jetson-course/ch05/turtlebot3_fortress ~/jetson-course/ch05/tb3_course ~/tb3_ws/src/
cd ~/tb3_ws
colcon build --symlink-install

# Step 2　載入工作空間並確認
echo "source ~/tb3_ws/install/setup.bash" >> ~/.bashrc
echo "export TURTLEBOT3_MODEL=burger" >> ~/.bashrc
source ~/.bashrc
ros2 pkg list | grep -E "turtlebot3_fortress|tb3_course"   # 應顯示兩個套件名稱
```

| 指令／設定 | 說明 |
|---|---|
| `colcon build` | 編譯 src 內的所有套件，產生 build、install、log 資料夾 |
| `--symlink-install` | 修改 .py 後不須重新編譯；修改 setup.py 則須重新編譯 |
| `install/setup.bash` | 將工作空間內的套件加入搜尋路徑 |
| `TURTLEBOT3_MODEL` | 指定機器人型號；TurtleBot3 的遙控、建圖與導航套件依此載入對應的參數 |

> **注意**
> - 尚未下載課程資料夾者，先執行 `cd ~ && git clone https://github.com/at44565685/jetson-course.git`。
> - 上課與作業一律修改 `~/tb3_ws/src` 內的檔案，不要修改 `~/jetson-course` 內的原檔，以免之後 `git pull` 發生衝突。

| 套件 | 內容 |
|---|---|
| `turtlebot3_fortress` | TurtleBot3 Burger 模型、TurtleBot3 World 場景與啟動檔 |
| `tb3_course` | 本章範例程式：`obstacle_stop`、`drive_distance`、`patrol` |

## 5.4.4 啟動檔

```bash
ros2 launch <套件> <啟動檔> [參數:=值 ...]
ros2 launch turtlebot3_fortress turtlebot3_world.launch.py --show-args    # 列出可用的參數
ros2 launch turtlebot3_fortress turtlebot3_world.launch.py gui:=false rviz:=true
```

| 參數 | 預設值 | 說明 |
|---|---|---|
| `x_pose`、`y_pose` | `-2.0`、`-0.5` | 車子的初始位置（空白場景為 `0.0`、`0.0`） |
| `gui` | `true` | `false` 時不開 Gazebo 視窗，運算負擔較低；以 RViz 觀察 |
| `rviz` | `false` | `true` 時開啟 RViz，顯示車體、TF、里程計與光達 |

**`simulation.launch.py` 的架構**（位於 `turtlebot3_fortress/launch`）

| 行號 | 內容 |
|---|---|
| 24–46 | `launch_gazebo()`：依參數組成 `ign gazebo` 指令，並以 ros_gz_sim 將車子載入場景 |
| 60–82 | 定義 ros_gz_bridge、robot_state_publisher 與 RViz 三個節點 |
| 84–97 | `LaunchDescription`：宣告啟動參數，並列出要執行的內容 |

## 5.4.5 啟動模擬與遙控

```bash
ros2 launch turtlebot3_fortress turtlebot3_world.launch.py     # 終端機 1：啟動模擬
ros2 run turtlebot3_teleop teleop_keyboard                     # 終端機 2：鍵盤遙控

# 空白場景（不含障礙物）
ros2 launch turtlebot3_fortress empty_world.launch.py

# 檢查模擬速度（real_time_factor 約 0.8 為正常）
ign topic -e -t /world/turtlebot3_world/stats -n 1 | grep real_time_factor
```

| 按鍵 | 作用 | Burger 上限 |
|---|---|---|
| w／x | 增加／減少前進速度 | 0.22 公尺／秒 |
| a／d | 增加／減少旋轉角速度 | 2.84 弧度／秒 |
| s 或空白鍵 | 立即停止 | — |

## 5.4.6 模擬系統的組成

```bash
rqt_graph                               # 取消勾選 Hide: Leaf topics 可看到所有主題
ros2 topic info /cmd_vel -v             # 查看發布者與訂閱者
```

| 主題 | 訊息型別 | 方向 |
|---|---|---|
| `/scan` | `sensor_msgs/msg/LaserScan` | Gazebo → ROS 2 |
| `/odom` | `nav_msgs/msg/Odometry` | Gazebo → ROS 2 |
| `/tf` | `tf2_msgs/msg/TFMessage` | Gazebo → ROS 2 |
| `/clock` | `rosgraph_msgs/msg/Clock` | Gazebo → ROS 2 |
| `/joint_states` | `sensor_msgs/msg/JointState` | Gazebo → ROS 2 |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | ROS 2 → Gazebo |

## 5.4.7 光達資料

```bash
ros2 topic hz /scan                     # 約 5 Hz
ros2 topic echo /scan --once
```

| 欄位 | 數值 | 意義 |
|---|---|---|
| `header.frame_id` | base_scan | 量測所依據的座標系（光達本體） |
| `angle_min`／`angle_max` | 0.0／6.28 | 掃描起訖角度（弧度），0 為車頭正前方 |
| `angle_increment` | 0.0175 | 相鄰兩點的角度差，約 1° |
| `range_min`／`range_max` | 0.12／3.5 | 有效量測範圍（公尺） |
| `ranges[i]` | 360 筆 | 第 i 點的距離；超出範圍者為 `.inf` |

**換算**：第 i 點的角度 = angle_min + i × angle_increment；`ranges[0]` 為正前方、`ranges[90]` 約為左方、`ranges[270]` 約為右方。

## 5.4.8 座標轉換 TF

```bash
ros2 run tf2_tools view_frames                       # 產生 frames.pdf
ros2 run tf2_ros tf2_echo odom base_footprint        # 即時顯示兩座標系的相對位置
```

| 座標轉換 | 發布者 | 性質 |
|---|---|---|
| map → odom | Cartographer 或 AMCL | 定位結果，修正里程計的誤差 |
| odom → base_footprint | Gazebo 差速驅動外掛 | 里程計，隨車輪轉動更新 |
| base_footprint → 感測器 | robot_state_publisher | 依 URDF，固定不變 |

## 5.5 撰寫第一個節點：obstacle_stop

**套件結構**

```text
tb3_course/
├── package.xml           # 套件資訊與相依套件
├── setup.py              # 執行檔進入點（entry_points）
├── resource/tb3_course
└── tb3_course/
    ├── obstacle_stop.py
    ├── drive_distance.py
    └── patrol.py
```

**程式架構**（`obstacle_stop.py`）：訂閱 `/scan` → 計算正前方最近距離 → 發布 `/cmd_vel`（前進或停車）

| 行號 | 內容 |
|---|---|
| 13–17 | 匯入 rclpy、Node、`qos_profile_sensor_data` 與兩種訊息型別 |
| 23–26 | 節點名稱 `obstacle_stop`，宣告三個參數 |
| 28–30 | 建立 `/cmd_vel` 發布者與 `/scan` 訂閱者 |
| 34–46 | `front_min_distance()`：計算正前方 ±`front_angle` 度內的最近有效距離 |
| 48–61 | `on_scan()`：判斷是否受阻並發布速度；狀態改變時才輸出記錄 |
| 63–77 | `stop()` 與 `main()`：`rclpy.spin()` 持續處理訊息，Ctrl＋C 結束時先停車 |

| 參數 | 預設值 | 說明 |
|---|---|---|
| `stop_distance` | 0.4 | 停車距離（公尺） |
| `forward_speed` | 0.15 | 前進速度（公尺／秒） |
| `front_angle` | 15 | 前方偵測範圍（度，左右各半） |

```bash
# 執行
ros2 launch turtlebot3_fortress turtlebot3_world.launch.py            # 終端機 1
ros2 run tb3_course obstacle_stop --ros-args -p use_sim_time:=true    # 終端機 2

# 於執行中修改參數（終端機 3）
ros2 param list /obstacle_stop
ros2 param get /obstacle_stop stop_distance
ros2 param set /obstacle_stop stop_distance 0.8      # 停車距離改為 0.8 公尺
ros2 param set /obstacle_stop forward_speed 0.05     # 降低前進速度
ros2 param set /obstacle_stop front_angle 45         # 擴大偵測範圍
```

**正常輸出**：車子由預設位置出發，正前方為柱子，約在距離 0.4 公尺處停下。

```text
[INFO] [obstacle_stop]: 前進：前方最近距離 inf m
[INFO] [obstacle_stop]: 停車：前方最近距離 0.39 m
```

> **注意**
> - 修改 `.py` 後不需重新編譯：工作空間以 `--symlink-install` 編譯，重新執行 `ros2 run` 即生效。修改 `setup.py`（例如新增執行檔）時則須重新 `colcon build`。

---

## 5.6 SLAM 建圖

```bash
ros2 launch turtlebot3_fortress turtlebot3_world.launch.py                      # 終端機 1
ros2 launch turtlebot3_cartographer cartographer.launch.py use_sim_time:=True   # 終端機 2（自動開啟 RViz）
ros2 run turtlebot3_teleop teleop_keyboard                                      # 終端機 3
```

| RViz 畫面 | 意義 |
|---|---|
| 淺灰色 | 已確認的可通行區域 |
| 黑色 | 障礙物 |
| 深灰色 | 尚未掃描的區域 |
| 紅點 | 光達目前的掃描結果；與黑色邊界重合表示定位正確 |

> **注意**
> - 以低速遙控車子繞行整個場地，轉彎時放慢；最後回到起點附近，使 Cartographer 修正整張地圖（迴路閉合）。

## 5.6.1 儲存地圖

```bash
ros2 run nav2_map_server map_saver_cli -f ~/map      # 產生 ~/map.pgm 與 ~/map.yaml
```

| `map.yaml` 欄位 | 意義 |
|---|---|
| `resolution` | 每像素代表的距離（0.05 公尺） |
| `origin` | 圖片左下角於地圖座標中的位置 |
| `occupied_thresh`／`free_thresh` | 判定為障礙物／可通行的門檻 |

## 5.7 Nav2 導航

```bash
# 先以 Ctrl＋C 結束 Cartographer；模擬可保持執行
ros2 launch turtlebot3_fortress turtlebot3_world.launch.py           # 終端機 1
ros2 launch turtlebot3_navigation2 navigation2.launch.py \
  use_sim_time:=True map:=$HOME/map.yaml                             # 終端機 2（自動開啟 RViz）
```

| 步驟 | RViz 操作 |
|---|---|
| Step 1　設定初始位置 | 點選 `2D Pose Estimate`，在車子實際位置按住並拖曳出車頭方向；光達紅點與地圖牆壁重合即完成定位 |
| Step 2　指定導航終點 | 點選 `Nav2 Goal`，在地圖空白處按住並拖曳出終點的位置與方向 |

| 組成 | 功能 |
|---|---|
| AMCL | 比對光達與已知地圖，估計車子在地圖中的位置（發布 map → odom） |
| 全域代價地圖 | 於障礙物周圍加上安全距離（膨脹層），供路徑規劃使用 |
| Planner Server | 規劃自目前位置至終點的路徑 |
| 區域代價地圖 | 依即時光達資料更新車子周圍的障礙物 |
| Controller Server | 依路徑計算速度指令，發布 `/cmd_vel` |
| BT Navigator | 以行為樹協調上述元件；受阻時執行原地旋轉、後退等恢復行為 |

## 5.7.1 以程式導航：patrol

```bash
# 先完成 5.7 的 Step 1（2D Pose Estimate）
ros2 run tb3_course patrol --ros-args -p use_sim_time:=true
# 再於 RViz 以 Publish Point 依序點選巡邏點

# 指定巡邏點數量與圈數
ros2 run tb3_course patrol --ros-args -p use_sim_time:=true -p num_points:=4 -p loops:=2
```

| 參數 | 預設值 | 說明 |
|---|---|---|
| `num_points` | 3 | 巡邏點數量 |
| `loops` | 1 | 巡邏圈數 |

| 行號 | 內容 |
|---|---|
| 25–33 | `make_pose()`：建立 `map` 座標系的目標位姿；z = sin(θ/2)、w = cos(θ/2) |
| 38–42 | `BasicNavigator` 本身即為節點，宣告並讀取參數 |
| 46–49 | 等待 Nav2 啟動及 AMCL 回報位置（初始位置由使用者於 RViz 設定） |
| 51–62 | 訂閱 `/clicked_point`，收集 Publish Point 點選的巡邏點 |
| 64–87 | 依序以 `goToPose()` 送出目標，讀取回饋（剩餘距離）與結果 |

**正常輸出**

```text
[INFO] [basic_navigator]: 請在 RViz 以 Publish Point 依序點選 3 個巡邏點
[INFO] [basic_navigator]: 第 1 點：x=1.20, y=0.35
...
[INFO] [basic_navigator]: 第 1 點到達
...
[INFO] [basic_navigator]: 巡邏結束
```

## 課後作業：drive_distance

```bash
ros2 run tb3_course drive_distance --ros-args -p use_sim_time:=true -p distance:=0.5
```

| 參數 | 預設值 | 說明 |
|---|---|---|
| `distance` | 1.0 | 前進距離（公尺） |
| `speed` | 0.1 | 前進速度（公尺／秒） |

1. 閱讀 `drive_distance.py`，說明其如何判斷已到達目標距離，以及實際距離為何會略大於設定值。
2. 仿照 `drive_distance`，撰寫原地旋轉 90° 的節點 `turn_angle`（提示：比較偏航角的變化；四元數換算見 `yaw_from_quaternion()`，第 19–23 行）。
3. 撰寫一個 launch 檔，同時啟動模擬與 `obstacle_stop`（啟動檔之寫法見 5.4.4）。

---

## 常見問題

| 現象 | 原因 | 處理方式 |
|---|---|---|
| `ros2: command not found` | 尚未載入 ROS 2 環境 | `source /opt/ros/humble/setup.bash`，並寫入 `~/.bashrc`（5.2.3） |
| `Unable to locate package ros-humble-…` | 尚未加入 ROS 2 套件來源，或未執行 `apt update` | 依 5.2.1 Step 2 設定後執行 `sudo apt update` |
| 5.2.1 Step 2 的 `echo $V $C` 沒有顯示版本號 | 無法連線至 GitHub | 確認網路連線後重新執行該步驟 |
| Gazebo 開不起來或畫面卡住 | 前一次的 Gazebo 程序未完全結束 | 執行下方清除指令後重新啟動 |
| 模擬非常緩慢（RTF 遠低於 0.8） | 經 MobaXterm 遠端顯示 Gazebo | 改於 Jetson 本機桌面執行；或加 `gui:=false rviz:=true` |
| `KeyError: 'TURTLEBOT3_MODEL'` | 未設定機器人型號 | `export TURTLEBOT3_MODEL=burger`，並寫入 `~/.bashrc`（5.4.3 Step 2） |
| `Package 'tb3_course' not found` | 套件未複製到工作空間、未編譯或未載入 | 確認位於 `~/tb3_ws/src`（5.4.3 Step 1），執行 `colcon build` 後 `source ~/tb3_ws/install/setup.bash` |
| 車子不會動 | `/cmd_vel` 無訂閱者，或 Gazebo 處於暫停 | `ros2 topic info /cmd_vel` 確認有訂閱者；確認 Gazebo 左下角為播放狀態 |
| rqt_graph 一片空白 | 未選擇顯示模式，或主題被隱藏 | 選擇 `Nodes/Topics (all)`，取消勾選 Hide 選項後按重新整理 |
| RViz 沒有地圖或車體 | 未使用模擬時間 | Cartographer／Nav2 啟動時加 `use_sim_time:=True` |
| `patrol` 一直顯示「等待初始位置」 | 尚未設定初始位置 | 於 RViz 以 `2D Pose Estimate` 標出車子位置 |
| 巡邏點顯示未到達（FAILED） | 點選位置位於障礙物或膨脹層內，無法規劃路徑；或定位錯誤 | 確認光達紅點與地圖牆壁重合，巡邏點選在地圖白色區域中央 |
| 與其他同學的機器人互相干擾 | 未限制通訊範圍 | 設定 `ROS_LOCALHOST_ONLY=1`（5.2.3），重開終端機 |

```bash
# 清除殘留的 Gazebo 與 ROS 2 程序
pkill -9 -f "ign gazebo"; pkill -9 -f ruby; ros2 daemon stop

# 確認環境變數
echo $ROS_DISTRO $ROS_LOCALHOST_ONLY $TURTLEBOT3_MODEL     # 應顯示 humble 1 burger
```
