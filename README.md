# Jetson Orin Nano 邊緣運算與深度視覺

課程用的範例指令與環境建置筆記。上課時請依下方「下載方式」把內容下載到自己的 Jetson Orin Nano。

## 適用環境

| 項目 | 內容 |
|---|---|
| 運算平台 | Jetson Orin Nano 8GB 開發者套件 |
| 系統版本 | JetPack 6.2 系列 |
| 攝影機 | USB 網路攝影機；Intel RealSense D435i（第四章） |

## 下載方式

在 Jetson 的終端機執行：

```bash
# 第一次上課：下載整個課程資料夾
cd ~
git clone https://github.com/<你的帳號>/<repo 名稱>.git

# 之後每次上課：取得更新的內容
cd ~/<repo 名稱>
git pull
```

## 內容

| 檔案 | 對應章節 | 內容 |
|---|---|---|
| [ch03_jetson-inference.md](ch03_jetson-inference.md) | 第三章 3.2 | JetPack 6.1／6.2 的 TensorRT 版本問題與 Docker 容器解法；imageNet、detectNet、segNet、poseNet、actionNet、backgroundNet、depthNet 的指令與可用模型 |
| [ch04_realsense.md](ch04_realsense.md) | 第四章 4.1–4.2 | 以 libuvc 編譯安裝 RealSense SDK、RealSense Viewer 操作、Python 範例執行方式、常見問題 |

## 使用提醒

- 筆記中的指令可直接複製貼到終端機執行；`<model>` 這類角括號內容需換成實際的名稱。
- 要修改範例程式時，請先複製一份再改（例如 `cp ex3-3.py my_ex3-3.py`），避免之後 `git pull` 時發生衝突。
- `git pull` 出現錯誤時，先執行 `git status` 查看是哪個檔案被修改過。

## 參考資源

- [dusty-nv/jetson-inference](https://github.com/dusty-nv/jetson-inference)：第三章使用的深度學習推論函式庫
- [cavedunissin/edgeai_jetson_orin](https://github.com/cavedunissin/edgeai_jetson_orin)：第四章使用的 Python 範例程式
- [librealsense](https://github.com/realsenseai/librealsense)：RealSense SDK 原始碼與安裝腳本
