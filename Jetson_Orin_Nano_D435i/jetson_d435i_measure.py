#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jetson Orin Nano + Intel RealSense D435i 工件尺寸量測（單檔版）。

使用方式：
  1. 將 D435i 以 USB 3.x 接至 Jetson Orin Nano，攝影機固定朝向平坦桌面。
  2. 桌面先清空，開啟程式；按 R 框選「只有桌面」的量測區域。
  3. 按 C 取樣空桌面深度、擬合桌面 3D 平面並校正。
  4. 放上可見頂面且高度足夠的工件，讀取畫面/終端機中的長寬高（mm）。
  5. 按 S 保存目前量測及畫面；按 Q 離開。

注意：本程式使用平面以上的 3D 點雲估計工件「可見外形」的平面長寬及高度。
      適合固定相機下，放在平坦桌面上的矩形或簡單外形工件原型測試；
      非計量檢定儀器，不保證任意形狀、遮擋或反光工件的真實尺寸。
"""

# 引入命令列參數模組，讓解析度、ROI 與閾值能自行設定，不把工件尺寸寫死。
import argparse
# 引入 CSV 模組，用來儲存每次按 S 的尺寸量測紀錄。
import csv
# 引入日期模組，用來產生檔案名稱與量測時間。
from datetime import datetime
# 引入路徑模組，確保輸出路徑可在 Jetson Linux 正常運作。
from pathlib import Path
# 引入時間模組，限制終端機輸出的更新間隔。
import time
# 引入 Python 型別註記，方便閱讀與維護。
from typing import Optional

# 引入 OpenCV：顯示影像、尋找物件輪廓、計算外接旋轉矩形。
import cv2
# 引入 NumPy：處理 D435i 的點雲、平面方程式與遮罩。
import numpy as np


# 定義桌面平面：一個參考點、朝向攝影機的法向量、桌面上的兩條單位基底。
class TablePlane:
    # 將計算好的桌面平面參數存放在物件內。
    def __init__(self, origin: np.ndarray, normal: np.ndarray):
        # 設定平面上的一個原點，單位是公尺。
        self.origin = np.asarray(origin, dtype=np.float64)
        # 將法向量正規化，讓內積結果代表公尺距離。
        n = np.asarray(normal, dtype=np.float64)
        self.normal = n / np.linalg.norm(n)
        # 選取攝影機 X 軸，投影到桌面作為第一條桌面座標軸。
        e1 = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        e1 -= np.dot(e1, self.normal) * self.normal
        # 相機角度過於特殊時，改用攝影機 Y 軸避免數值不穩定。
        if np.linalg.norm(e1) < 1e-6:
            e1 = np.array([0.0, 1.0, 0.0], dtype=np.float64)
            e1 -= np.dot(e1, self.normal) * self.normal
        # 第一個桌面單位向量。
        self.axis_u = e1 / np.linalg.norm(e1)
        # 第二個桌面單位向量，與第一軸、平面法向量互相垂直。
        self.axis_v = np.cross(self.normal, self.axis_u)
        self.axis_v /= np.linalg.norm(self.axis_v)

    # 計算點雲中每個點距離桌面的有號高度，單位為公尺。
    def heights(self, points: np.ndarray) -> np.ndarray:
        # 正數代表點位於桌面朝攝影機方向，理論上就是工件高出桌面的部分。
        return np.sum((points - self.origin) * self.normal, axis=-1)

    # 將相機座標的 3D 點轉成平面上的 2D 座標，單位為公尺。
    def project_to_table(self, points: np.ndarray) -> np.ndarray:
        # 用桌面第一軸計算水平座標 u。
        u = np.sum((points - self.origin) * self.axis_u, axis=-1)
        # 用桌面第二軸計算水平座標 v。
        v = np.sum((points - self.origin) * self.axis_v, axis=-1)
        # 組合為 Nx2 的點陣列，可交給 OpenCV 計算旋轉外接矩形。
        return np.stack((u, v), axis=-1)


# 從空桌面點雲中使用 RANSAC 找出桌面平面，減少錯誤深度值的干擾。
def fit_table_plane(points: np.ndarray, tolerance_m: float,
                    iterations: int, min_inlier_ratio: float) -> TablePlane:
    # 只使用有限的三維座標，排除 NaN 與 Inf。
    xyz = np.asarray(points, dtype=np.float64).reshape(-1, 3)
    xyz = xyz[np.isfinite(xyz).all(axis=1)]
    # 桌面有效點太少就停止，避免產生誤導性的尺寸。
    if len(xyz) < 300:
        raise ValueError('桌面可用深度點不足，請確認光線、USB 連線、距離或 ROI。')
    # 設定固定亂數種子，讓同一批資料的校正結果可重現。
    rng = np.random.default_rng(42)
    # 隨機採樣部分有效點，降低在 Jetson 上的 RANSAC 運算量。
    if len(xyz) > 7000:
        xyz = xyz[rng.choice(len(xyz), size=7000, replace=False)]
    # 先建立最佳平面及最佳內點遮罩的儲存空間。
    best_mask = None
    best_count = 0
    # 反覆使用三個點嘗試建立平面。
    for _ in range(iterations):
        # 隨機選三個不同的桌面點。
        sample = xyz[rng.choice(len(xyz), size=3, replace=False)]
        # 以外積求平面法向量。
        normal = np.cross(sample[1] - sample[0], sample[2] - sample[0])
        # 如果三點共線或太近，跳過這一輪。
        norm = np.linalg.norm(normal)
        if norm < 1e-8:
            continue
        # 正規化法向量。
        normal /= norm
        # 計算所有樣本點至該候選平面的垂直距離。
        distances = np.abs((xyz - sample[0]) @ normal)
        # 判斷距離小於允許誤差的桌面內點。
        inliers = distances < tolerance_m
        # 計算當次桌面內點數量。
        count = int(np.count_nonzero(inliers))
        # 保留內點數最多的候選平面。
        if count > best_count:
            best_count = count
            best_mask = inliers
    # 若找不到具有一定比例的桌面平面，拒絕校正。
    if best_mask is None or best_count < max(300, int(len(xyz) * min_inlier_ratio)):
        raise ValueError('桌面平面校正失敗：ROI 可能包含牆壁、物體或深度雜訊。')
    # 取出真正貼近桌面的內點，再用 SVD 重新估計最佳平面。
    inlier_points = xyz[best_mask]
    # 用內點平均位置當作平面原點。
    origin = np.mean(inlier_points, axis=0)
    # SVD 的最後一個右奇異向量是最佳擬合平面的法向量。
    _, _, vh = np.linalg.svd(inlier_points - origin, full_matrices=False)
    normal = vh[-1]
    # 確保法向量朝向攝影機原點 (0,0,0)，如此工件高度應為正值。
    if float(np.dot(normal, -origin)) < 0:
        normal *= -1
    # 傳回完成的平面物件。
    return TablePlane(origin, normal)


# 將畫面 ROI 限制在影像內，避免索引越界。
def clip_roi(roi: tuple[int, int, int, int], width: int, height: int):
    # 先取出 ROI 左上角與寬高。
    x, y, w, h = roi
    # 將左上角修正為非負值。
    x, y = max(0, x), max(0, y)
    # 避免 ROI 超出右下角或變成負值。
    w, h = min(w, width-x), min(h, height-y)
    # ROI 必須大於一定像素，才能得到可用平面與物件輪廓。
    if w < 30 or h < 30:
        raise ValueError('ROI 尺寸太小或超出影像範圍。')
    # 傳回有效 ROI。
    return x, y, w, h


# 解析使用者可選填的命令列 ROI，例如 80,60,480,360。
def parse_roi(text: str) -> Optional[tuple[int, int, int, int]]:
    # 如果未指定，則使用 None，待程式取得影像後再選擇。
    if not text.strip():
        return None
    # 將逗號分隔字串轉成整數。
    vals = tuple(int(v.strip()) for v in text.split(','))
    # 一定要有 x,y,w,h 四個數值。
    if len(vals) != 4:
        raise ValueError('--roi 請使用 x,y,w,h，例如 80,60,480,360。')
    # 傳回 ROI 座標。
    return vals


# 建立待測桌面遮罩：只擷取高於桌面且具有有效深度的區域。
def create_foreground_mask(points: np.ndarray, plane: TablePlane,
                           roi: tuple[int, int, int, int],
                           min_h_m: float, max_h_m: float) -> tuple[np.ndarray, np.ndarray]:
    # 從每一個 3D 點求相對桌面的高度。
    heights = plane.heights(points)
    # 有效深度：非零、非無窮大、且有正常的 Z 距離。
    valid = np.isfinite(points).all(axis=2) & (points[:, :, 2] > 0)
    # 只保留位於高度範圍的物件點。
    foreground = valid & (heights >= min_h_m) & (heights <= max_h_m)
    # 建立一張空白 ROI 遮罩。
    roi_mask = np.zeros(foreground.shape, dtype=np.uint8)
    # 在使用者選取的 ROI 區域填入白色。
    x, y, w, h = roi
    roi_mask[y:y+h, x:x+w] = 255
    # 將 ROI 與候選工件的條件做交集。
    mask = np.where(foreground & (roi_mask > 0), 255, 0).astype(np.uint8)
    # 傳回二值遮罩以及每個像素的有號高度。
    return mask, heights


# 根據 3D 工件點及桌面平面，計算真正有單位的長度、寬度、高度。
def measure_masked_objects(points: np.ndarray, plane: TablePlane,
                           mask: np.ndarray, heights: np.ndarray,
                           roi: tuple[int, int, int, int],
                           min_area_px: int, min_points: int,
                           max_objects: int, kernel_size: int,
                           height_percentile: float) -> tuple[list[dict], np.ndarray]:
    # 建立可設定大小的形態學結構元素，以清除孤立噪聲。
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    # 先用開運算去除小噪點。
    clean = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    # 再用閉運算補上小縫隙。
    clean = cv2.morphologyEx(clean, cv2.MORPH_CLOSE, kernel)
    # 用 OpenCV 找出分離的物件輪廓。
    contours, _ = cv2.findContours(clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # 先按像素面積由大到小排序。
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    # 儲存輸出的物件尺寸。
    results = []
    # 取得 ROI 邊界，以判定工件是否被影像裁切。
    rx, ry, rw, rh = roi
    # 逐個輪廓取得尺寸，直到達到使用者指定的最大物件數。
    for contour in contours:
        # 面積過小通常代表深度雜訊，直接跳過。
        if cv2.contourArea(contour) < min_area_px:
            continue
        # 將輪廓轉成外接矩形。
        bx, by, bw, bh = cv2.boundingRect(contour)
        # 接觸 ROI 邊界的工件可能被截斷，不能回報可靠長寬。
        if bx <= rx+2 or by <= ry+2 or bx+bw >= rx+rw-2 or by+bh >= ry+rh-2:
            continue
        # 為這個輪廓建立自己的實心遮罩。
        component = np.zeros(clean.shape, dtype=np.uint8)
        cv2.drawContours(component, [contour], -1, 255, thickness=cv2.FILLED)
        # 只保留該輪廓中確實具備量測深度的點。
        valid = (component > 0) & (mask > 0)
        # 取出所有物件 3D 點，單位公尺。
        work_points = points[valid]
        # 有效 3D 點數太少則不測量。
        if len(work_points) < min_points:
            continue
        # 將工件三維點正投影回桌面，避免直接把像素當作毫米。
        planar_coords = plane.project_to_table(work_points)
        # 把公尺換成 mm，並轉為 OpenCV 需要的 float32。
        planar_mm = np.asarray(planar_coords * 1000.0, dtype=np.float32)
        # 將桌面投影中的工件範圍，轉成最小旋轉外接矩形。
        rectangle = cv2.minAreaRect(planar_mm.reshape(-1, 1, 2))
        # 矩形長寬是兩條桌面方向邊長，單位 mm。
        side_a, side_b = rectangle[1]
        # 長度取較長的一邊，不依賴工件在畫面中的旋轉角度。
        length_mm = max(float(side_a), float(side_b))
        # 寬度取較短的一邊，完全由點雲計算，沒有寫死 120.3。
        width_mm = min(float(side_a), float(side_b))
        # 高度取工件 3D 點對桌面的穩健百分位，降低單點尖峰影響。
        height_mm = float(np.percentile(heights[valid], height_percentile) * 1000.0)
        # 尺寸不得為負數或無效浮點數。
        if not np.isfinite([length_mm, width_mm, height_mm]).all():
            continue
        # 使用輪廓中心當作繪製文字的參考位置。
        cx, cy = bx + bw // 2, by + bh // 2
        # 儲存此次工件尺寸和繪圖所需資訊。
        results.append({'id': len(results)+1, 'length_mm': length_mm,
                        'width_mm': width_mm, 'height_mm': height_mm,
                        'bbox': (bx, by, bw, bh), 'center': (cx, cy),
                        'valid_points': int(len(work_points))})
        # 若達到指定量測數量，便停止迴圈以節省算力。
        if len(results) >= max_objects:
            break
    # 傳回尺寸結果及消除雜訊後的遮罩。
    return results, clean


# 讀取命令列選項，避免把設備序號、相機解析度、閾值或尺寸寫死在程式中。
def build_arguments() -> argparse.Namespace:
    # 建立 argparse。
    ap = argparse.ArgumentParser(description='Jetson Orin Nano + D435i 直接量測桌面工件尺寸（mm）')
    # 可選設備序號，預設為自動尋找 D435i。
    ap.add_argument('--serial', default='', help='指定 RealSense 序號；空白時自動選取 D435i')
    # 使用 D435i 常見支援的深度／彩色串流解析度與 FPS，可自行調整。
    ap.add_argument('--width', type=int, default=640, help='彩色／深度影像寬度')
    ap.add_argument('--height', type=int, default=480, help='彩色／深度影像高度')
    ap.add_argument('--fps', type=int, default=15, help='擷取 FPS')
    # 可以輸入固定 ROI；不填時可按 R 滑鼠框選。
    ap.add_argument('--roi', type=str, default='', help='選定桌面 ROI：x,y,width,height')
    # 此選項適用沒有 Jetson 桌面、只使用 SSH 終端機的情況。
    ap.add_argument('--no-window', action='store_true', help='不顯示 OpenCV 視窗，仍在終端機輸出量測')
    # 可調整螢幕上的視窗寬度，輸出量測與運算仍用原始解析度。
    ap.add_argument('--display-width', type=int, default=960, help='OpenCV 顯示寬度')
    # 設定從桌面到工件的最低高度，可依相機噪聲調整，單位 mm。
    ap.add_argument('--min-height-mm', type=float, default=10.0, help='最小有效工件高度（mm）')
    # 設定可量測的最大工件高度，超過此值不加入遮罩。
    ap.add_argument('--max-height-mm', type=float, default=300.0, help='最大有效工件高度（mm）')
    # 平面校正允許的點至平面誤差；數值太大可能把非桌面也當桌面。
    ap.add_argument('--plane-tolerance-mm', type=float, default=5.0, help='桌面 RANSAC 擬合容差（mm）')
    # 可設定空桌面擷取的影格數量，減少單張深度的噪聲。
    ap.add_argument('--calibration-frames', type=int, default=12, help='校正空桌面時取樣張數')
    # 調整 RANSAC 次數。
    ap.add_argument('--ransac-iterations', type=int, default=140, help='桌面平面 RANSAC 次數')
    # 桌面內點至少應達到 ROI 深度樣本的一定比例。
    ap.add_argument('--min-inlier-ratio', type=float, default=0.50, help='校正桌面的最低平面內點比例')
    # 排除較小的工件候選區域或深度雜訊。
    ap.add_argument('--min-area-px', type=int, default=650, help='最小工件輪廓面積（像素）')
    # 有效深度樣本不足的工件不要回報尺寸。
    ap.add_argument('--min-points', type=int, default=250, help='工件至少需要的有效 3D 點數')
    # 可自行決定一次要量測幾個工件。
    ap.add_argument('--max-objects', type=int, default=3, help='最多同時量測工件數')
    # 降低影格分析頻率，Jetson 效能不夠時可加大。
    ap.add_argument('--measure-every', type=int, default=2, help='每隔幾張攝影機影格量測一次')
    # 設定消除深度噪點用的形態學 kernel；需為正奇數。
    ap.add_argument('--kernel', type=int, default=5, help='形態學濾波核尺寸（奇數）')
    # 高度用百分位估計而不是最大值，避免少數點雜訊造成過大高度。
    ap.add_argument('--height-percentile', type=float, default=95.0, help='估計高度所用百分位數')
    # 控制終端機印出尺寸的時間間隔。
    ap.add_argument('--print-every', type=float, default=1.0, help='終端機尺寸輸出間隔（秒）')
    # 可自行設定輸出檔案路徑。
    ap.add_argument('--output-dir', type=str, default='measurement_results', help='保存紀錄與截圖的資料夾')
    # 解析命令列參數。
    args = ap.parse_args()
    # 驗證必要參數，避免 OpenCV 對無效值產生莫名錯誤。
    if args.width <= 0 or args.height <= 0 or args.fps <= 0:
        ap.error('width、height、fps 必須大於 0')
    if args.display_width <= 0 or args.measure_every < 1 or args.max_objects < 1:
        ap.error('display-width、measure-every、max-objects 必須大於 0')
    if args.kernel < 1 or args.kernel % 2 == 0:
        ap.error('kernel 必須為正奇數')
    if not 0 < args.height_percentile <= 100 or not 0 < args.min_inlier_ratio <= 1:
        ap.error('height-percentile 與 min-inlier-ratio 超出允許範圍')
    if args.min_height_mm <= 0 or args.max_height_mm <= args.min_height_mm:
        ap.error('max-height-mm 必須大於 min-height-mm，且最小高度要大於 0')
    if args.min_area_px < 1 or args.min_points < 3 or args.calibration_frames < 1:
        ap.error('min-area-px、min-points、calibration-frames 設定無效')
    if args.plane_tolerance_mm <= 0 or args.ransac_iterations < 1 or args.print_every <= 0:
        ap.error('plane-tolerance-mm、ransac-iterations、print-every 必須大於 0')
    # 傳回經過驗證的設定。
    return args


# 從 RealSense SDK 的點雲頂點轉成 NumPy Nx3 / HxWx3 公尺座標。
def vertices_to_xyz(vertices, h: int, w: int) -> np.ndarray:
    # 使用 NumPy 取得 SDK 提供的頂點陣列。
    raw = np.asanyarray(vertices)
    # 將 SDK 的 3 個 float32 座標視為連續記憶體。
    coords = raw.view(np.float32).reshape(h, w, 3)
    # 轉成獨立連續陣列，避免下一個影格更新緩衝區造成資料被覆寫。
    return np.ascontiguousarray(coords)


# 在桌面校正時取多張樣本，並擬合桌面平面。
def calibrate_table(camera, roi, args) -> TablePlane:
    # 準備所有空桌面取樣點。
    sample_list = []
    # 將 ROI 拆成 x,y,w,h。
    x, y, w, h = roi
    # 設定取樣亂數產生器。
    rng = np.random.default_rng(123)
    # 拍攝指定數量的空桌面影格。
    for i in range(args.calibration_frames):
        # 從連接在 Jetson 的 D435i 直接擷取深度及顏色。
        _, pts = camera.read()
        # 只保留指定 ROI 的桌面深度點。
        area = pts[y:y+h, x:x+w].reshape(-1, 3)
        # 排除 SDK 報告為無效的深度點。
        area = area[np.isfinite(area).all(axis=1) & (area[:, 2] > 0)]
        # 每張影格取適量點，避免佔用 Jetson 過多記憶體。
        if len(area) > 1300:
            area = area[rng.choice(len(area), 1300, replace=False)]
        # 儲存本影格樣本。
        if len(area):
            sample_list.append(area)
        # 在終端機印出校正進度。
        print(f'\r[校正] 取樣 {i+1}/{args.calibration_frames}', end='', flush=True)
    # 換行，以免最後的校正訊息和結果印在一起。
    print()
    # 確認至少取得部分桌面有效資料。
    if not sample_list:
        raise ValueError('無法擷取桌面有效深度，請確認相機與工作距離。')
    # 用 RANSAC 與 SVD 找出桌面幾何平面。
    plane = fit_table_plane(np.concatenate(sample_list, axis=0),
                            args.plane_tolerance_mm/1000.0,
                            args.ransac_iterations, args.min_inlier_ratio)
    # 顯示校正結果：桌面中心離相機的距離，單位 mm。
    print(f'[校正完成] 相機到桌面參考點距離：約 {np.linalg.norm(plane.origin)*1000:.1f} mm')
    # 傳回桌面平面供後續工件量測使用。
    return plane


# 包裝直接讀取 D435i 的 RealSense SDK 操作，沒有 Raspberry Pi/網路/LCM。
class RealSenseCamera:
    # 使用指定參數建立相機物件，但尚未啟動 USB 串流。
    def __init__(self, args):
        # 只有真的要啟動 D435i 時才 import SDK，方便單元測試其他函數。
        try:
            import pyrealsense2 as rs
        except ImportError as exc:
            raise RuntimeError('缺少 pyrealsense2：請先在 Jetson 安裝支援 ARM64 的 librealsense Python bindings。') from exc
        # 暫存 SDK 模組。
        self.rs = rs
        # 儲存使用者設定。
        self.args = args
        # 建立 RealSense pipeline。
        self.pipeline = rs.pipeline()
        # 建立串流設定。
        config = rs.config()
        # 列出已接上的 RealSense 相機。
        devices = list(rs.context().query_devices())
        # 沒有偵測到任何相機就停止。
        if not devices:
            raise RuntimeError('找不到 RealSense，請確認 D435i 已以 USB 3.x 接上 Jetson，並執行 rs-enumerate-devices。')
        # 印出所有可用裝置資訊。
        for d in devices:
            print('[裝置]', d.get_info(rs.camera_info.name), '序號:', d.get_info(rs.camera_info.serial_number))
        # 使用者指定序號時直接選擇該裝置。
        serial = args.serial.strip()
        # 未指定序號時，自動尋找 D435i（不區分大小寫）。
        if not serial:
            for d in devices:
                if 'D435I' in d.get_info(rs.camera_info.name).upper():
                    serial = d.get_info(rs.camera_info.serial_number)
                    break
        # 如果只找到其他 RealSense 型號則顯示清楚提示。
        if not serial:
            raise RuntimeError('未找到 D435i；若設備名稱不同，請使用 --serial 指定序號。')
        # 設定選取的攝影機序號。
        config.enable_device(serial)
        # 啟用彩色影像串流。
        config.enable_stream(rs.stream.color, args.width, args.height, rs.format.bgr8, args.fps)
        # 啟用 16-bit 深度影像串流。
        config.enable_stream(rs.stream.depth, args.width, args.height, rs.format.z16, args.fps)
        # 啟動直接位於 Jetson USB 的 RealSense 相機。
        try:
            self.profile = self.pipeline.start(config)
        except RuntimeError as exc:
            raise RuntimeError('D435i 串流啟動失敗。請檢查 USB 3.x、供電或 --width/--height/--fps。') from exc
        # 啟用將深度對齊至彩色影像的處理器。
        self.align = rs.align(rs.stream.color)
        # 啟用 SDK 的 3D 點雲處理器，可用相機自身內參把深度轉成公尺座標。
        self.pointcloud = rs.pointcloud()
        # 顯示測到的深度尺度；程式直接使用 SDK 的米制點雲，不需手動寫死轉換係數。
        scale = self.profile.get_device().first_depth_sensor().get_depth_scale()
        print(f'[相機啟動] RealSense D435i，{args.width}x{args.height}@{args.fps}，深度單位={scale:.8f} m/unit')
        # 丟掉幾張起始影格，等待自動曝光與深度資料穩定。
        for _ in range(12):
            self.pipeline.wait_for_frames()

    # 從相機取得一張彩色影像及對齊後的 3D 點雲。
    def read(self):
        # 等待下一組同步的彩色與深度影格。
        frames = self.pipeline.wait_for_frames(5000)
        # 將深度畫面對齊到彩色畫面座標。
        aligned = self.align.process(frames)
        # 取得對齊後的深度影格。
        depth_frame = aligned.get_depth_frame()
        # 取得彩色影格。
        color_frame = aligned.get_color_frame()
        # 若任一影格缺失，回報錯誤供主程式決定是否重試。
        if not depth_frame or not color_frame:
            raise RuntimeError('RealSense 某一張彩色或深度影格無效。')
        # 轉成 OpenCV 使用的 BGR 影像，並複製避免緩衝區覆寫。
        color = np.asanyarray(color_frame.get_data()).copy()
        # 呼叫 RealSense SDK 將深度點轉成 XYZ 公尺座標，避免用像素直接估尺寸。
        cloud = self.pointcloud.calculate(depth_frame)
        # 轉換 SDK 的點雲頂點緩衝區為 HxWx3 NumPy 陣列。
        xyz = vertices_to_xyz(cloud.get_vertices(), color.shape[0], color.shape[1])
        # 傳回影像與公尺點雲。
        return color, xyz

    # 停止 SDK USB 串流，確保程式離開時釋放 D435i。
    def stop(self):
        # 停止並關閉 RealSense 串流。
        self.pipeline.stop()


# 在畫面上標示工件輪廓、長寬高，文字使用英文字母避免 OpenCV 中文亂碼。
def draw_overlay(color: np.ndarray, roi, results, calibrated: bool) -> np.ndarray:
    # 複製影像，避免修改原始彩色影像。
    canvas = color.copy()
    # 繪製使用者選定的桌面 ROI。
    x, y, w, h = roi
    cv2.rectangle(canvas, (x, y), (x+w, y+h), (0, 255, 255), 2)
    # 顯示校正狀態；未校正時不可相信任何毫米結果。
    status = 'CALIBRATED' if calibrated else 'NOT CALIBRATED - EMPTY TABLE THEN PRESS C'
    cv2.putText(canvas, status, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.57,
                (60, 235, 60) if calibrated else (0, 60, 255), 2, cv2.LINE_AA)
    # 在視窗下方顯示按鍵操作提示。
    cv2.putText(canvas, 'R: ROI   C: CALIBRATE   S: SAVE   Q: QUIT',
                (12, canvas.shape[0]-15), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (240,240,240), 2, cv2.LINE_AA)
    # 逐個量測結果畫出外框和毫米數值。
    for item in results:
        bx, by, bw, bh = item['bbox']
        # 綠框表示通過有效深度與輪廓條件的工件。
        cv2.rectangle(canvas, (bx, by), (bx+bw, by+bh), (30, 230, 30), 2)
        # 顯示工件編號與長度。
        label1 = f"#{item['id']} L={item['length_mm']:.1f} W={item['width_mm']:.1f} mm"
        # 顯示工件高度。
        label2 = f"H={item['height_mm']:.1f} mm"
        # 避免標籤畫到視窗之外。
        tx = min(max(4, bx), max(4, canvas.shape[1]-270))
        ty = max(65, by-32)
        cv2.putText(canvas, label1, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (0,255,0), 2, cv2.LINE_AA)
        cv2.putText(canvas, label2, (tx, ty+22), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (0,255,0), 2, cv2.LINE_AA)
    # 傳回完成標示的影像。
    return canvas


# 把當下的尺寸結果存到 CSV，並儲存畫面以利人工驗證。
def save_measurement(output_dir: Path, color: np.ndarray, results: list[dict]) -> None:
    # 確保輸出資料夾存在。
    output_dir.mkdir(parents=True, exist_ok=True)
    # 使用目前日期時間做唯一識別名稱。
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    # 指定存圖路徑。
    image_file = output_dir / f'measurement_{timestamp}.png'
    # 寫出量測標示畫面。
    cv2.imwrite(str(image_file), color)
    # 指定尺寸 CSV，集中放在同一個檔案中。
    csv_file = output_dir / 'measurements.csv'
    # 判斷檔案是否第一次建立，以便建立欄位標題。
    need_header = not csv_file.exists()
    # 開啟 CSV 檔案，避免 Windows/Excel 讀取時中文欄位亂碼。
    with csv_file.open('a', encoding='utf-8-sig', newline='') as f:
        # 建立 CSV 寫入物件。
        writer = csv.writer(f)
        # 新檔案加入欄位說明。
        if need_header:
            writer.writerow(['timestamp', 'object_id', 'length_mm', 'width_mm',
                             'height_mm', 'valid_points', 'image'])
        # 逐個工件寫下計算出來的長寬高，而非固定常數。
        for item in results:
            writer.writerow([timestamp, item['id'], f"{item['length_mm']:.2f}",
                             f"{item['width_mm']:.2f}", f"{item['height_mm']:.2f}",
                             item['valid_points'], str(image_file)])
    # 把完成的檔案位置列印在 Jetson 終端機。
    print(f'[已儲存] 畫面：{image_file}，量測 CSV：{csv_file}')


# 主程式：一支 Python 完成 D435i 擷取、桌面校正、尺寸量測、輸出。
def main() -> int:
    # 讀取命令列參數，所有相機及演算法設定皆可調整。
    args = build_arguments()
    # 解析使用者在 CLI 指定的 ROI。
    requested_roi = parse_roi(args.roi)
    # 建立輸出資料夾位置。
    output_dir = Path(args.output_dir).expanduser()
    # 宣告相機物件，讓 finally 在任何例外發生時都能安全關閉。
    camera = None
    # 尚未校正時將平面保留為 None。
    plane = None
    # 記錄上一次終端機輸出時間。
    last_print_time = 0.0
    # 將上一次的量測結果預設為空。
    latest_results = []
    # 計算目前攝影機影格編號。
    frame_index = 0
    # 先提示使用者正確的校正流程。
    print('=== Jetson Orin Nano + D435i 單機工件尺寸量測 ===')
    print('請固定 D435i、清空桌面；先選桌面 ROI，再校正，不要在校正後移動相機。')
    # try/finally 可以在按 Q、Ctrl+C 或錯誤時關閉相機。
    try:
        # 直接啟動 Jetson USB 所連接的 D435i。
        camera = RealSenseCamera(args)
        # 讀取第一張畫面，取得真實的影像寬高。
        first_color, _ = camera.read()
        image_h, image_w = first_color.shape[:2]
        # 沒有指定 ROI 時，預設為中央 80% 視野作為起始值，可按 R 重新框選。
        roi = clip_roi(requested_roi or (image_w//10, image_h//10,
                                          image_w*8//10, image_h*8//10), image_w, image_h)
        # 若是無視窗模式，必須以終端機操作開始校正。
        if args.no_window:
            # 避免遠端 SSH 不知道目前 ROI 而量到背景。
            print(f'[無視窗] ROI={roi}。若需要自訂桌面，請加 --roi x,y,w,h。')
            # 等待確認桌面沒有任何工件後，才擷取桌面平面。
            input('確認桌面已清空且相機固定，按 Enter 開始桌面校正...')
            # 取得校正的桌面平面。
            plane = calibrate_table(camera, roi, args)
        # 有 GUI 的 Jetson 桌面顯示時建立可縮放視窗。
        else:
            # 建立 OpenCV 視窗，預設使用可調整尺寸的視窗。
            cv2.namedWindow('Jetson D435i Workpiece Measurement', cv2.WINDOW_NORMAL)
            # 顯示按鍵操作提示。
            print('[GUI] R=桌面 ROI；C=空桌面校正；S=儲存量測；Q=離開。')
        # 不斷讀取 D435i 畫面。
        while True:
            # 將 frame_index 增加 1。
            frame_index += 1
            # 從 D435i 取得目前彩色影像與公尺點雲。
            color, xyz = camera.read()
            # 如果相機重新調整了串流大小，重新取得目前尺寸。
            h, w = color.shape[:2]
            # 先使用上一次的尺寸結果，避免沒分析的影格閃爍。
            results = latest_results
            # 尚未校正時禁止輸出工件尺寸。
            if plane is not None and frame_index % args.measure_every == 0:
                # 求工件相對桌面的高度遮罩。
                mask, heights = create_foreground_mask(
                    xyz, plane, roi, args.min_height_mm/1000.0,
                    args.max_height_mm/1000.0)
                # 根據 3D 點雲及工件輪廓計算長、寬、高。
                results, _ = measure_masked_objects(
                    xyz, plane, mask, heights, roi, args.min_area_px,
                    args.min_points, args.max_objects, args.kernel, args.height_percentile)
                # 更新畫面上要顯示的結果。
                latest_results = results
                # 定期把長寬高輸出到終端機，避免每張影格都大量刷屏。
                if time.monotonic() - last_print_time >= args.print_every:
                    # 沒偵測到工件時也給明確提示。
                    if not results:
                        print('[量測] 未找到符合條件的工件，或工件接觸 ROI 邊緣 / 深度無效。')
                    # 逐個工件列印真實計算結果，單位毫米。
                    for obj in results:
                        print(f"[量測] 工件#{obj['id']}  長={obj['length_mm']:.1f} mm  "
                              f"寬={obj['width_mm']:.1f} mm  高={obj['height_mm']:.1f} mm  "
                              f"(有效點={obj['valid_points']})")
                    # 記住輸出時間。
                    last_print_time = time.monotonic()
            # 無視窗模式下只輸出終端機，避免在 SSH/X11 缺席時 imshow 當掉。
            if args.no_window:
                continue
            # 把 ROI、校正狀態、尺寸資訊直接畫在彩色影像上。
            annotated = draw_overlay(color, roi, results, plane is not None)
            # 顯示時保持影像比例，避免把工件形狀拉伸。
            disp_w = min(args.display_width, w)
            disp_h = round(h * disp_w / w)
            # 只縮小顯示，不改動真正 3D 點雲的解析度。
            displayed = cv2.resize(annotated, (disp_w, disp_h), interpolation=cv2.INTER_AREA)
            # 顯示在 Jetson 本機桌面視窗中。
            cv2.imshow('Jetson D435i Workpiece Measurement', displayed)
            # 偵測使用者按鍵，1ms 待機。
            key = cv2.waitKey(1) & 0xFF
            # 按 Q 或 ESC 時離開。
            if key in (ord('q'), 27):
                break
            # 按 R 時在目前畫面重新框選桌面 ROI。
            if key == ord('r'):
                # selectROI 用滑鼠拖曳，Enter 確認，Esc 取消。
                selected = cv2.selectROI('Jetson D435i Workpiece Measurement',
                                         annotated, showCrosshair=True, fromCenter=False)
                # 若確實選到矩形就更新 ROI。
                if selected[2] > 0 and selected[3] > 0:
                    roi = clip_roi(tuple(int(n) for n in selected), w, h)
                    # ROI 改變後舊的桌面平面可能不適用，強制重新校正。
                    plane = None
                    latest_results = []
                    print(f'[ROI] 已更新為 {roi}。請清空桌面並按 C 重新校正。')
            # 按 C 讓使用者校正空桌面。
            if key == ord('c'):
                # 校正時不允許使用舊的工件尺寸結果。
                plane = None
                latest_results = []
                # 開始讀取多張深度影格擬合平面。
                try:
                    plane = calibrate_table(camera, roi, args)
                except ValueError as exc:
                    print('[校正失敗]', exc)
            # 按 S 將目前畫面與工件尺寸存檔。
            if key == ord('s'):
                # 未校正或未找到物件時拒絕產生不可信的尺寸紀錄。
                if plane is None or not latest_results:
                    print('[儲存] 尚未校正或沒有可量測工件，請先校正並放置工件。')
                else:
                    save_measurement(output_dir, annotated, latest_results)
    # 使用者按 Ctrl+C 時讓程式正常結束。
    except KeyboardInterrupt:
        print('\n[停止] 使用者中斷量測。')
    # RealSense 或其他操作錯誤時給出易懂資訊。
    except (RuntimeError, ValueError, OSError) as exc:
        print('[錯誤]', exc)
        return 1
    # 最後必須關閉所有鏡頭資源。
    finally:
        # 確保無論成功失敗都會停用 D435i USB 串流。
        if camera is not None:
            camera.stop()
        # OpenCV 有視窗時關閉視窗，不留下殘餘畫面。
        if not args.no_window:
            cv2.destroyAllWindows()
    # 正常執行到這裡表示程式結束。
    return 0


# Python 主入口：直接使用 python3 jetson_d435i_measure.py 即可啟動。
if __name__ == '__main__':
    # 使用 SystemExit 把執行結果傳回 Jetson Linux 終端機。
    raise SystemExit(main())
