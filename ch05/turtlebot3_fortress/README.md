# turtlebot3_fortress

在 Jetson Orin Nano（JetPack 6、ROS 2 Humble）上以 Gazebo Fortress 模擬 TurtleBot3 Burger。

TurtleBot3 官方的 Humble 模擬套件使用 Gazebo Classic，無法安裝於 Jetson（arm64）。本套件將官方 Jazzy 版的車體模型、網格與 TurtleBot3 World 場景改寫為 Gazebo Fortress 的格式；建圖、導航與鍵盤遙控沿用 TurtleBot3 官方的 Humble 套件。

模型、網格與場景取自 [ROBOTIS-GIT/turtlebot3_simulations](https://github.com/ROBOTIS-GIT/turtlebot3_simulations)（Apache License 2.0）。

## 修改內容

| 項目 | 修改 |
|---|---|
| 外掛名稱 | `gz-sim-*` 改為 Fortress 的 `ignition-gazebo-*` |
| 座標系名稱 | `gz_frame_id` 改為 `ignition_frame_id` |
| 場景 | 地面與光源改為內建模型，不需連網下載；關閉陰影 |
| 運算負擔 | IMU 由 200 Hz 降為 50 Hz；不繪製光達射線 |
| 速度指令 | `/cmd_vel` 使用 `geometry_msgs/msg/Twist`，與 Humble 的 teleop、Nav2 一致 |

## 安裝

```bash
# 1. Gazebo Fortress 與 ROS 2 套件
sudo apt update
sudo apt install -y ignition-fortress ros-humble-ros-gz \
  ros-humble-turtlebot3-teleop ros-humble-turtlebot3-cartographer \
  ros-humble-turtlebot3-navigation2 ros-humble-navigation2 ros-humble-nav2-bringup

# 2. 將課程套件複製到工作空間並編譯
cd ~/jetson-course && git pull
mkdir -p ~/tb3_ws/src
cp -r ~/jetson-course/ch05/turtlebot3_fortress ~/jetson-course/ch05/tb3_course ~/tb3_ws/src/
cd ~/tb3_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
echo "source ~/tb3_ws/install/setup.bash" >> ~/.bashrc
echo "export TURTLEBOT3_MODEL=burger" >> ~/.bashrc
source ~/.bashrc
```

## 使用

```bash
# 模擬（TurtleBot3 World）
ros2 launch turtlebot3_fortress turtlebot3_world.launch.py

# 空白場景
ros2 launch turtlebot3_fortress empty_world.launch.py

# 鍵盤遙控（另開終端機）
ros2 run turtlebot3_teleop teleop_keyboard

# SLAM 建圖（另開終端機，會自動開啟 RViz）
ros2 launch turtlebot3_cartographer cartographer.launch.py use_sim_time:=True

# 儲存地圖
ros2 run nav2_map_server map_saver_cli -f ~/map

# Nav2 導航（先結束 SLAM，模擬保持執行）
ros2 launch turtlebot3_navigation2 navigation2.launch.py use_sim_time:=True map:=$HOME/map.yaml
```

### 啟動參數

| 參數 | 預設值 | 說明 |
|---|---|---|
| `x_pose`、`y_pose` | `-2.0`、`-0.5` | 車子的初始位置（空白場景為 `0.0`、`0.0`） |
| `gui` | `true` | `false` 時只執行 Gazebo 伺服器、不開視窗，運算負擔較低；以 RViz 觀察 |
| `rviz` | `false` | `true` 時開啟 RViz，顯示車體、TF、里程計與光達 |

範例：`ros2 launch turtlebot3_fortress turtlebot3_world.launch.py gui:=false rviz:=true`

## 檢查模擬速度

```bash
ign topic -e -t /world/turtlebot3_world/stats -n 1 | grep real_time_factor
```

`real_time_factor` 接近 1.0 表示模擬與真實時間同步。

## 疑難排解

| 現象 | 處理 |
|---|---|
| Gazebo 開不起來 | 先清除殘留程序：`pkill -9 -f "ign gazebo"; pkill -9 -f ruby; ros2 daemon stop` |
| `KeyError: 'TURTLEBOT3_MODEL'` | 執行 `export TURTLEBOT3_MODEL=burger` |
| 車子不會動 | 確認 `ros2 topic info /cmd_vel` 有訂閱者；確認 Gazebo 左下角不是暫停狀態 |
| RViz 沒有地圖或車體 | 確認 Cartographer／Nav2 啟動時有加 `use_sim_time:=True` |
