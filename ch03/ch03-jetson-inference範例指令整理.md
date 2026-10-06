# 第三章　jetson-inference 範例指令整理（JetPack 6.1／6.2）

## 問題說明

JetPack 6.1／6.2 內建的 TensorRT 升到了 10.3，NVIDIA 在這一版移除了對舊 Caffe 模型格式的支援。`imagenet.py` 的預設模型 GoogleNet 是 Caffe 格式（`bvlc_googlenet.caffemodel`），所以一載入就失敗。

NVIDIA 論壇的官方說法是：要直接跑 jetson-inference，請使用 JetPack 6.0（TensorRT 8.6）。

## 解決方式：改用官方 Docker 容器

r36.3.0 版的容器裡面自帶舊版 TensorRT。

```bash
cd ~/jetson-inference
docker/run.sh --container dustynv/jetson-inference:r36.3.0

# 進入容器後
cd build/aarch64/bin
```

> **注意**
> - 各模型於第一次使用時會自動下載，並進行 TensorRT 最佳化，需等待數分鐘。
> - 以 SSH 連線、無法開啟顯示視窗時，可加上 `--headless`。
> - 想在主機上保留結果，請將輸出存到 `images/test/`（對應主機的 `~/jetson-inference/data/images/test/`）。

---

## 3.2.2 圖像辨識（imageNet）

**`--network` 可用模型**

| 模型 |
|---|
| `googlenet`（預設）、`googlenet-12`、`alexnet` |
| `resnet-18`、`resnet-50`、`resnet-101`、`resnet-152` |
| `vgg-16`、`vgg-19`、`inception-v4` |

```bash
# 單張影像
python3 ./imagenet.py ./images/black_bear.jpg ./images/test/black_bear_ima.jpg

# 即時攝影機（USB／CSI）
python3 ./imagenet.py /dev/video0
python3 ./imagenet.py csi://0

# 批次處理多張影像
python3 ./imagenet.py "images/cat_*.jpg" \
        "images/test/cat_%i.jpg"

# 更換模型並列出前 5 名
python3 ./imagenet.py --network=resnet-18 \
        --topK=5 /dev/video0
```

## 3.2.3 物件偵測（detectNet）

**`--network` 可用模型**

| 模型 | 偵測類別 |
|---|---|
| `ssd-mobilenet-v2`（預設）、`ssd-mobilenet-v1`、`ssd-inception-v2` | COCO 91 類 |
| `peoplenet`、`peoplenet-pruned` | person、bag、face |
| `dashcamnet`、`trafficcamnet` | person、car、bike、sign |
| `facedetect` | face |

```bash
python3 detectnet.py images/airplane_1.jpg \
        images/airplane_1det.jpg
python3 detectnet.py /dev/video0 output.mp4
```

## 3.2.4 圖像分割（segNet）

**`--network` 可用模型**（格式：`fcn-resnet18-<資料集>-<解析度>`；省略解析度時載入最低解析度版本）

| 資料集（場景） | 模型 |
|---|---|
| Pascal VOC（一般物體，預設） | `fcn-resnet18-voc-320x320`（預設）、`fcn-resnet18-voc-512x320` |
| Cityscapes（街道） | `fcn-resnet18-cityscapes-512x256`、`-1024x512`、`-2048x1024` |
| DeepScene（戶外步道） | `fcn-resnet18-deepscene-576x320`、`-864x480` |
| Multi-Human（人體部位） | `fcn-resnet18-mhp-512x320` |
| SUN RGB-D（室內） | `fcn-resnet18-sun-512x400`、`-640x512` |

```bash
# 單張影像
python3 ./segnet.py ./images/horse_0.jpg \
        ./images/horse0_seg.jpg

# 更換模型
python3 ./segnet.py \
  --network=fcn-resnet18-deepscene \
  ./images/horse_0.jpg ./images/horse_0seg.jpg

# --visualize：mask（只輸出色塊）或 overlay（疊加於原圖）
python3 ./segnet.py --network=fcn-resnet18-deepscene --visualize=overlay \
        ./images/trail_0.jpg ./images/trail_0_overlay.jpg

# --alpha：色塊透明度（0–255）
python3 ./segnet.py --alpha=200 \
  ./images/room_5.jpg \
  ./images/room_5_alpha200.jpg

# --filter-mode：point 或 linear
python3 ./segnet.py \
  --filter-mode=point \
  ./images/peds_0.jpg \
  ./images/peds_0_point.jpg

# 即時影像
python3 ./segnet.py --network=<model> /dev/video0             # 常見的 USB 攝影機
python3 ./segnet.py --network=<model> csi://0                 # MIPI CSI 匯流排攝影機
python3 ./segnet.py --network=<model> /dev/video0 output.mp4  # 將結果儲存為影片檔
```

## 3.2.5 姿態估計（poseNet）

**`--network` 可用模型**

| 模型 | 關鍵點 |
|---|---|
| `resnet18-body`（預設）、`densenet121-body` | 人體 18 個 |
| `resnet18-hand` | 手部 21 個 |

```bash
# 單張影像
python3 ./posenet.py ./images/humans_1.jpg \
        ./images/pose_humans_1.jpg

# 即時影像
python3 ./posenet.py --network=<model> /dev/video0             # 常見的 USB 攝影機
python3 ./posenet.py --network=<model> csi://0                 # MIPI CSI 匯流排攝影機
python3 ./posenet.py --network=<model> /dev/video0 output.mp4  # 將結果儲存為影片檔
```

## 3.2.6 動作辨識（actionNet）

**`--network` 可用模型**：`resnet18`（預設）、`resnet34`（皆為 1040 種動作）

```bash
# 單張影像
python3 ./actionnet.py ./images/humans_4.jpg \
        ./images/humans_4_action.jpg

# 即時影像
python3 ./actionnet.py /dev/video0              # 常見的 USB 攝影機
python3 ./actionnet.py /dev/video0 output.mp4   # 將結果儲存為影片檔
```

## 3.2.7 背景移除（backgroundNet）

**`--network` 可用模型**：`u2net`（唯一模型，通常不需指定）

```bash
# 單張影像
python3 ./backgroundnet.py ./images/bird_0.jpg ./images/bird_0_mask.jpg          # 移除背景
python3 ./backgroundnet.py --replace=./images/coral.jpg \
        ./images/bird_0.jpg ./images/bird_0_replace.jpg                          # 更換背景

# 即時影像
python3 ./backgroundnet.py /dev/video0                             # 常見的 USB 攝影機
python3 ./backgroundnet.py --replace=images/coral.jpg /dev/video0  # 更換背景
python3 ./backgroundnet.py csi://0                                 # MIPI CSI 匯流排攝影機
python3 ./backgroundnet.py --network=<model> /dev/video0 output.mp4  # 儲存為影片檔
```

## 3.2.8 距離估計（depthNet）

**`--network` 可用模型**：`fcn-mobilenet`（預設）、`fcn-resnet18`、`fcn-resnet50`

```bash
# 單張影像
python3 ./depthnet.py ./images/room_1.jpg ./images/room_1_depth.jpg

# 即時影像
python3 ./depthnet.py /dev/video0              # 常見的 USB 攝影機
python3 ./depthnet.py csi://0                  # MIPI CSI 匯流排攝影機
python3 ./depthnet.py /dev/video0 output.mp4   # 將結果儲存為影片檔
```
