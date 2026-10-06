# 第四章　RealSense 安裝與範例指令整理（JetPack 6.2.2）

## 問題說明

RealSense SDK 存取攝影機的方式有兩種：

| 方式 | 作法 | 在 JetPack 6.2.2 上 |
|---|---|---|
| 核心驅動 | 經由作業系統核心內的驅動程式存取攝影機 | 核心缺少 D435i 所需的驅動程式（HID 感測器驅動），無法使用 |
| libuvc | 由 SDK 內建的 USB 通訊程式直接存取攝影機，不經核心驅動 | 可使用 |

以 apt 或 ROS 2 套件安裝的 SDK 屬於第一種，開啟 D435i 時會出現 `bad optional access`。

## 解決方式：自行編譯採用 libuvc 的 SDK

使用 RealSense 提供的 `libuvc_installation.sh`，在 Jetson 上下載原始碼並編譯出採用 libuvc 的 SDK，不需更動作業系統核心。

```bash
cd ~
wget https://github.com/realsenseai/librealsense/raw/master/scripts/libuvc_installation.sh
chmod +x ./libuvc_installation.sh
./libuvc_installation.sh
```

> **注意**
> - 執行腳本前須拔除攝影機；Step 1–4 完成後再接上。
> - 工具程式安裝於 `/usr/local/bin`，原始碼位於 `~/librealsense_build/librealsense-master`；Python 範例位於其中的 `wrappers/python/examples`。
> - 已安裝 ROS 2 RealSense 套件（`ros-humble-librealsense2`）的系統，`/opt/ros/humble/bin` 內另有同名工具，且搜尋順序在前，該版本無法開啟 D435i。本課程的工具一律以完整路徑 `/usr/local/bin/…` 執行；ROS 2 的套件不需移除。
> - 安裝過程不需更新攝影機韌體。

---

## 4.1.3 在 Jetson Orin Nano 上安裝 RealSense 套件

**安裝環境**

| 項目 | 內容 |
|---|---|
| 運算平台 | Jetson Orin Nano 開發者套件，JetPack 6.2.2（L4T 36.5） |
| 景深攝影機 | Intel RealSense D435i，以 USB 3 傳輸線連接 |
| SDK 原始碼 | `~/librealsense_build/librealsense-master` |
| 工具程式 | `/usr/local/bin` |

```bash
# Step 1　執行 libuvc 安裝腳本（先拔除攝影機）
cd ~
wget https://github.com/realsenseai/librealsense/raw/master/scripts/libuvc_installation.sh
chmod +x ./libuvc_installation.sh
./libuvc_installation.sh
# 顯示「Librealsense script completed」即完成建置

# Step 2　建置 Python 套件 pyrealsense2
sudo apt-get install python3-dev
cd ~/librealsense_build/librealsense-master/build
cmake ../ -DFORCE_LIBUVC=true -DCMAKE_BUILD_TYPE=release \
  -DBUILD_PYTHON_BINDINGS=bool:true -DPYTHON_EXECUTABLE=$(which python3)
make -j2
sudo make install
python3 -c "import pyrealsense2 as rs; print(rs.__version__)"   # 顯示版本號即完成安裝

# Step 3　準備 Python 範例資料夾
cd ~
git clone https://github.com/cavedunissin/edgeai_jetson_orin
cp ~/edgeai_jetson_orin/ch04/*.py \
   ~/librealsense_build/librealsense-master/wrappers/python/examples/

# Step 4　安裝相依套件並重新開機
sudo apt-get install libcanberra-gtk-module libcanberra-gtk3-module
sudo reboot

# Step 5　確認 USB 3 連線（接上攝影機）
lsusb | grep 8086        # 應出現 ID 8086:0b3a（Depth Camera 435i）
lsusb -t                 # 攝影機（Class=Video）所在列應為 5000M

# Step 6　確認 SDK 可存取攝影機
sudo ldconfig
/usr/local/bin/rs-enumerate-devices
```

**Step 2 的 cmake 參數**

| 參數 | 作用 |
|---|---|
| `-DFORCE_LIBUVC=true` | 採用 libuvc，與 Step 1 的設定一致 |
| `-DBUILD_PYTHON_BINDINGS=bool:true` | 產生 Python 套件 pyrealsense2 |
| `-DPYTHON_EXECUTABLE=$(which python3)` | 指定套件所對應的 Python 直譯器 |

**Step 5 的正常輸出**（`5000M` 為 USB 3；`480M` 為 USB 2，須更換傳輸線或連接埠）

```text
/:  Bus 02.Port 1: Dev 1, Class=root_hub, Driver=tegra-xusb/4p, 10000M
    |__ Port 1: Dev 2, If 0, Class=Hub, Driver=hub/4p, 10000M
        |__ Port 2: Dev 3, If 0, Class=Video, Driver=uvcvideo, 5000M
```

**Step 6 的檢查欄位**

| 輸出欄位 | 正常情形 |
|---|---|
| `Name` | Intel RealSense D435I |
| `Product Id` | 0B3A |
| `Usb Type Descriptor` | 3.x；若為 2.1，表示仍為 USB 2 連線 |

> **注意**
> - Step 3 的 `cp` 會取代範例資料夾內的同名檔案；4.2 節的程式列表與行號，均以本課程的版本為準。

## 4.1.4 在 RealSense Viewer 中檢視深度影像

```bash
# 啟動 RealSense Viewer（須於 Jetson 所接的實體螢幕操作）
/usr/local/bin/realsense-viewer

# 列出系統中的所有版本
which -a realsense-viewer
```

| 操作 | 位置 |
|---|---|
| 確認型號與 USB 版本 | 左上角裝置名稱旁 |
| 開關深度影像／彩色影像 | `Stereo Module`／`RGB Camera` |
| 切換影像輸出模式（如 `Hand`） | `Preset` 選單 |
| 設定解析度、FPS、紅外線畫面、自動曝光、ROI | `Stereo Module` 下拉選單 |
| 切換 2D／3D 視角 | 右上角 `2D`／`3D` |

---

## 4.2 RealSense 的 Python 範例

```bash
cd ~/librealsense_build/librealsense-master/wrappers/python/examples
```

| 範例程式 | 用途 | 使用套件 |
|---|---|---|
| `python-tutorial-1-depth.py` | 在終端機以字元顯示深度 | pyrealsense2 |
| `align-depth2color.py` | 深度對齊 RGB，刪除指定距離外的背景 | pyrealsense2、NumPy、OpenCV |
| `opencv_viewer_example.py` | 以 OpenCV 視窗並排顯示 RGB 與深度 | pyrealsense2、NumPy、OpenCV |
| `opencv_viewer_example_v2.py` | 加入 Esc／q 按鍵結束 | pyrealsense2、NumPy、OpenCV |
| `opencv_singlepoint_viewer_example.py` | 顯示畫面中心點的距離 | pyrealsense2、NumPy、OpenCV |
| `opencv_facedistance_viewer_example.py` | 以 Haar 分類器偵測人臉並標示距離 | pyrealsense2、NumPy、OpenCV |

> **注意**
> - Python 範例可透過 MobaXterm 遠端登入後執行，影像以額外視窗顯示；亦可接實體螢幕測試。
> - 同一時間只能有一支程式使用攝影機；執行前須關閉 RealSense Viewer 與前一支程式。
> - 未設按鍵判斷的範例以 Ctrl＋C 結束。

## 4.2.1 範例一：在終端機顯示深度資訊

```bash
cd ~/librealsense_build/librealsense-master/wrappers/python/examples
python3 python-tutorial-1-depth.py
```

## 4.2.2 範例二：深度與 RGB 影像對齊

**可調整參數**：`clipping_distance_in_meters`（第 34 行，預設 1 公尺；超過此距離的像素以灰色取代）

```bash
cd ~/librealsense_build/librealsense-master/wrappers/python/examples
python3 align-depth2color.py

# 修改距離門檻後重新執行
nano align-depth2color.py
python3 align-depth2color.py
```

## 4.2.3 原廠範例 opencv_viewer_example.py

```bash
cd ~/librealsense_build/librealsense-master/wrappers/python/examples
python3 opencv_viewer_example.py
```

## 4.2.4 加入按鍵結束：opencv_viewer_example_v2.py

**修改內容**：將 `opencv_viewer_example.py` 第 44 行的 `cv2.waitKey(1)` 換成下列四行，另存為 `opencv_viewer_example_v2.py`。

```python
key = cv2.waitKey(1)
if key & 0xFF == ord('q') or key == 27:
    cv2.destroyAllWindows()
    break
```

```bash
cd ~/librealsense_build/librealsense-master/wrappers/python/examples
nano opencv_viewer_example.py            # 修改後按 Ctrl＋O 另存為 v2，再按 Ctrl＋X 離開
python3 opencv_viewer_example_v2.py      # 按 Esc 或 q 結束
```

## 4.2.5 取得單點深度資訊

**量測點**：畫面中心 (320, 240)，以 `depth_frame.get_distance(x, y)` 取得距離（公尺）

```bash
cd ~/librealsense_build/librealsense-master/wrappers/python/examples
python3 opencv_singlepoint_viewer_example.py
```

## 4.2.6 人臉辨識並取得臉部距離

**分類器路徑**：`opencv_facedistance_viewer_example.py` 第 43 行，須將 `/home/jetsonnano/` 改為實際的使用者目錄（可用 `echo $HOME` 查看）

```bash
# Step 1　下載 Haar 分類器（位於 opencv/data/haarcascades）
cd ~
git clone https://github.com/opencv/opencv.git

# Step 2　修改分類器路徑
cd ~/librealsense_build/librealsense-master/wrappers/python/examples
nano opencv_facedistance_viewer_example.py

# Step 3　執行
python3 opencv_facedistance_viewer_example.py
```

---

## 常見問題

| 現象 | 原因 | 處理方式 |
|---|---|---|
| `bad optional access` | 所執行的是經核心驅動存取攝影機的版本（`/opt/ros/humble/bin`） | 以 `/usr/local/bin` 的完整路徑執行（Step 6） |
| Viewer 顯示 USB 2.1，啟動串流後出現 `Frames didn't arrived within 5 seconds` | 以 USB 2 連線，頻寬不足 | 更換 USB 3 傳輸線或連接埠（Step 5） |
| `import pyrealsense2` 失敗 | 尚未建置 Python 套件，或安裝位置不在搜尋路徑內 | 依 Step 2 建置並安裝；仍失敗時依下方指令加入路徑 |
| 範例程式無法開啟攝影機 | 攝影機為 Viewer 或其他程式所佔用 | 關閉佔用攝影機的程式後重新執行 |

```bash
# 確認所執行的版本
which -a rs-enumerate-devices
ldd /usr/local/bin/rs-enumerate-devices | grep realsense    # 應指向 /usr/local/lib

# import pyrealsense2 失敗時：找出 pyrealsense2 資料夾，並將其所在目錄加入 PYTHONPATH
find /usr -type d -name pyrealsense2 2>/dev/null
export PYTHONPATH=$PYTHONPATH:<pyrealsense2 資料夾所在的目錄>
```

> **注意**
> - Viewer 提示更新韌體時，須先確認為 USB 3 連線，且不得安裝低於 `Min FW Version` 的版本。
