# 第六章　生成式 AI 應用與範例指令整理（JetPack 6.2）

## 課程環境

本章在 Jetson Orin Nano 上執行三項生成式 AI 應用：以 Ollama 執行大型語言模型（LLM）、以 Open WebUI 建立 RAG 知識庫問答，以及以 Stable Diffusion 生成圖片。所有模型皆在 Jetson 本機執行，不需連線至雲端服務。

| 項目 | 內容 |
|---|---|
| 運算平台 | Jetson Orin Nano 8GB 開發者套件，JetPack 6.2.x（L4T 36.5，CUDA 12.6） |
| 儲存空間 | 須使用 SSD；本章合計約需 25 GB |
| LLM 執行工具 | Ollama（原生安裝，服務埠號 11434） |
| 網頁介面 | Open WebUI（Docker 容器，埠號 8080） |
| 使用模型 | `gemma3:4b`、`qwen2.5:3b`（LLM）；`nomic-embed-text`（嵌入模型） |
| 圖片生成 | stable-diffusion-webui（jetson-containers 容器，埠號 7860），模型 Stable Diffusion 1.5 |

| 節次 | 內容 | 使用工具 |
|---|---|---|
| 第一節 | 生成式 AI 簡介、大型語言模型、參數量與量化；安裝 Ollama、執行與比較模型、API；Open WebUI 與模型設定 | Ollama、Open WebUI |
| 第二節 | LLM 的限制（幻覺）、RAG 原理、嵌入向量；建立知識庫、結果對照、檢索品質 | Open WebUI |
| 第三節 | 擴散模型、Stable Diffusion 的組成與參數；jetson-containers、啟動 stable-diffusion-webui、參數實驗 | stable-diffusion-webui |

> **注意**
> - Jetson Orin Nano 的 CPU 與 GPU 共用 8GB 記憶體，**同一時間只執行一個大型模型**。第三節開始前須先停止 Ollama 的模型與 Open WebUI（6.8.1 Step 1）。
> - 請以另一台電腦的瀏覽器開啟網頁介面（`http://<Jetson IP>:8080`、`http://<Jetson IP>:7860`）；在 Jetson 本機開啟瀏覽器會額外佔用記憶體。

**空間用量（教學機實測）**

| 項目 | 大小 |
|---|---|
| Ollama 程式與 GPU 函式庫 | 約 2.8 GB |
| 模型：`gemma3:4b`、`qwen2.5:3b`、`nomic-embed-text` | 約 5.5 GB |
| Open WebUI 映像檔 | 以 `docker images` 查看 |
| stable-diffusion-webui 映像檔 | 約 8.5 GB |
| Stable Diffusion 1.5 模型 | 約 4 GB |

---

## 6.1 生成式 AI 簡介

生成式 AI 是能產生新內容（文字、圖片、語音）的模型；第三章的影像分類、物件偵測則是對既有資料作出判斷，稱為判別式 AI。判別式 AI 的資料由多到少（一張圖片 → 一個類別），生成式 AI 的資料由少到多（幾個字 → 一張圖片），因此所需的模型規模與運算量通常遠大於判別式模型。

| 類型 | 代表技術 | 代表模型或服務 |
|---|---|---|
| 文字生成 | 大型語言模型（LLM） | ChatGPT、Gemma、Llama、Qwen |
| 圖片生成 | 擴散模型 | Stable Diffusion、DALL·E |
| 影像理解 | 視覺語言模型（VLM） | GPT-4o、Gemma 3 |
| 語音 | 語音辨識、語音合成 | Whisper |

| 年份 | 里程碑 |
|---|---|
| 2014 | 生成對抗網路（GAN）提出 |
| 2017 | Transformer 架構提出，成為大型語言模型的基礎 |
| 2020 | 擴散模型（DDPM）提出 |
| 2022 | Stable Diffusion 開源釋出；ChatGPT 發布 |
| 2023 起 | Llama、Gemma、Qwen 等開源小型模型推出，邊緣裝置亦可執行 |

## 6.1.1 於邊緣裝置執行生成式 AI

| 比較項目 | 雲端服務 | 邊緣裝置 |
|---|---|---|
| 資料隱私 | 提問內容須上傳至服務商 | 資料留在本機 |
| 網路 | 須連線 | 可離線運作 |
| 費用 | 依使用量計費 | 硬體一次投入 |
| 模型規模 | 數千億參數 | 受記憶體限制，約 4B 以下 |
| 回答品質 | 較佳 | 較弱，適合特定任務 |

---

## 6.2 大型語言模型

大型語言模型（LLM）以 Transformer 為架構，依據前文預測**下一個詞元**（token）；每次產生一個詞元，接回輸入後再預測下一個，反覆即形成完整的回答。模型輸出的是所有候選詞元的機率分布，並依此分布抽選，因此同一問題每次的回答可能不同。

| 溫度（temperature） | 選字方式 | 適用情境 |
|---|---|---|
| 低（0–0.3） | 幾乎都選機率最高的詞元，回答穩定 | 問答、知識庫查詢 |
| 中（0.7 左右） | 兼顧穩定與變化 | 一般對話 |
| 高（1 以上） | 較常選到低機率的詞元，回答多變 | 創意寫作、發想 |

## 6.2.1 參數量與量化

所需記憶體（位元組）≈ 參數量 × 每個參數的位元數 ÷ 8

| 數值精度 | 每個參數 | 4B 模型約需 |
|---|---|---|
| FP32 | 32 位元 | 16 GB |
| FP16 | 16 位元 | 8 GB |
| INT8 | 8 位元 | 4 GB |
| 4 位元量化（Q4） | 4 位元 | 約 2–2.5 GB |

Orin Nano 扣除系統後可用的記憶體約 5 GB，故須使用 4 位元量化的模型。Ollama 模型庫提供的模型預設皆已量化為 4 位元；模型名稱冒號後的 `4b`、`3b` 即參數量。

| 模型 | 參數量 | 下載大小 | 執行時記憶體 |
|---|---|---|---|
| `gemma3:4b`（Google） | 4B，可處理影像 | 3.3 GB | 2.9 GB |
| `qwen2.5:3b`（阿里巴巴） | 3B | 1.9 GB | 約 2.5 GB |

---

## 6.3 以 Ollama 執行 LLM

Ollama 整合模型下載、量化模型的推論與 API 服務；安裝後以 systemd 在背景執行，模型由推論引擎 llama.cpp 以 GPU 執行，模型檔為 GGUF 格式。

| 項目 | 說明 |
|---|---|
| 模型庫 | [ollama.com/library](https://ollama.com/library)，可查詢可用的模型與大小 |
| 程式位置 | `/usr/local/bin/ollama`；GPU 函式庫於 `/usr/local/lib/ollama` |
| 模型位置 | `/usr/share/ollama/.ollama/models` |
| 服務管理 | `systemctl status ollama`；開機自動啟動 |

## 6.3.1 安裝 Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama --version                        # 顯示版本號即表示安裝完成
systemctl status ollama --no-pager      # 應為 active (running)
```

安裝程式會偵測到 Jetson，另行下載 JetPack 6 專用的 GPU 函式庫（`/usr/local/lib/ollama/cuda_jetpack6`）。

> **注意**
> - 安裝檔約 2 GB。若下載中途出現 `PROTOCOL_ERROR` 而中斷，重新執行即可；多次失敗時，可先執行 `echo "--http1.1" >> ~/.curlrc` 改用 HTTP/1.1，安裝完成後再刪除該行。

## 6.3.2 下載與執行模型

```bash
ollama pull gemma3:4b
ollama run gemma3:4b --verbose "請用繁體中文，以三句話介紹 Jetson Orin Nano。"
```

```bash
# 另開終端機：確認模型是否於 GPU 上執行
ollama ps
```

**正常輸出（教學機）**

```text
load duration:        6.761502288s
prompt eval rate:     129.20 tokens/s
eval rate:            18.10 tokens/s

NAME        SIZE     PROCESSOR    CONTEXT    UNTIL
gemma3:4b   2.9 GB   100% GPU     4096       4 minutes from now
```

| 輸出 | 意義 |
|---|---|
| `load duration` | 將模型載入記憶體的時間 |
| `prompt eval rate` | 讀取提示詞的速度 |
| `eval rate` | 產生回答的速度（每秒詞元數） |
| `PROCESSOR` | `100% GPU` 表示模型完全於 GPU 上執行 |
| `UNTIL` | 模型閒置 5 分鐘後自動卸載 |

`ollama run` 不加提示詞時進入對話模式，輸入 `/bye` 結束。

**比較不同模型**

```bash
ollama pull qwen2.5:3b
ollama run qwen2.5:3b --verbose "請用繁體中文，以三句話介紹 Jetson Orin Nano。"
```

| 項目 | gemma3:4b | qwen2.5:3b |
|---|---|---|
| 生成速度 | 18.1 詞元／秒 | 22.7 詞元／秒 |
| 載入時間（首次） | 6.8 秒 | 4.4 秒 |
| 繁體中文 | 通順 | 夾雜大陸用語（如「人工智能」） |
| 工具呼叫 | 不支援 | 支援 |

## 6.3.3 Ollama 服務與 API

`ollama run` 與 Open WebUI 皆透過 11434 埠的 REST API 與模型溝通，自行撰寫的程式亦可用相同方式呼叫。

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "gemma3:4b",
  "prompt": "用一句話介紹邊緣運算",
  "stream": false
}'
```

| 指令 | 說明 |
|---|---|
| `ollama list` | 列出已下載的模型 |
| `ollama ps` | 列出目前載入記憶體的模型 |
| `ollama stop <模型>` | 立即卸載模型，釋放記憶體 |
| `ollama show <模型>` | 顯示模型的參數量、量化方式與上下文長度 |
| `ollama rm <模型>` | 刪除模型檔 |

---

## 6.4 Open WebUI 網頁介面

```bash
docker run -d --network=host \
  -v open-webui:/app/backend/data \
  -e OLLAMA_BASE_URL=http://127.0.0.1:11434 \
  --name open-webui --restart always \
  ghcr.io/open-webui/open-webui:main

docker logs -f open-webui      # 出現 OPEN WEBUI 字樣後按 Ctrl+C
```

| 參數 | 說明 |
|---|---|
| `--network=host` | 容器直接使用 Jetson 的網路，網頁埠號為 8080 |
| `-v open-webui:...` | 帳號、對話與知識庫存於 Docker volume，重啟後仍保留 |
| `OLLAMA_BASE_URL` | Ollama 服務的位址 |
| `--restart always` | Jetson 開機後自動啟動 |

以另一台電腦的瀏覽器開啟 `http://<Jetson IP>:8080`，**第一個註冊的帳號即為管理員**。

| 位置 | 功能 |
|---|---|
| 輸入框右側 | 切換模型（清單即 Ollama 已下載的模型） |
| 右上角「控制選項」 | 本次對話的系統提示詞、溫度等參數 |
| 左側「工作區」 | 管理知識庫（6.6） |
| 左下角帳號 →「管理員控制台」 | 模型與系統設定 |

```bash
# Open WebUI 的啟動與停止
docker stop open-webui
docker start open-webui
```

## 6.4.1 模型設定

管理員控制台 → 設定 → 模型 → 編輯 `gemma3:4b`：

| 設定 | 建議值與說明 |
|---|---|
| 內建工具 | **全部關閉**（見下方說明） |
| 系統提示詞 | 規定語言、語氣與角色，範例如下 |
| 上下文長度（進階參數） | 4096。愈長佔用愈多記憶體；8192 時記憶體幾乎用盡 |
| 溫度（進階參數） | 問答時調低，例如 0.2 |
| 函式呼叫（進階參數） | 預設 |

**系統提示詞範例**

```text
請一律使用台灣繁體中文與台灣常用詞彙回答，例如「人工智慧」而非「人工智能」、「程式」而非「程序」。
```

> **注意**
> - Open WebUI 預設以工具呼叫（tool calling）的形式將「內建工具」交給模型；`gemma3:4b` 在 Ollama 中不支援工具呼叫，未關閉時會出現 `does not support tools` 而無法回答。`qwen2.5:3b` 支援工具呼叫，不受影響。
> - 「函式呼叫」請維持「預設」；改為「原生」無法解決上述問題。

---

## 6.5 LLM 的限制

以第五章的內容詢問 `gemma3:4b`：

```text
TurtleBot3 模擬的工作空間路徑是什麼？鍵盤遙控要執行什麼指令？
```

| 問題 | 模型的回答（未提供課程資料） | 正確答案 |
|---|---|---|
| 工作空間路徑 | 邊長 2.0 公尺的正方形工作空間 | `~/tb3_ws` |
| 鍵盤遙控指令 | W／S／A／D 與方向鍵的按鍵表 | `ros2 run turtlebot3_teleop teleop_keyboard` |

模型不知道本課程的內容，卻仍以完整、肯定的格式作答，此即**幻覺**（hallucination）。

## 6.5.1 RAG 原理

檢索增強生成（Retrieval-Augmented Generation, RAG）於回答前先從文件中檢索相關段落，再將段落與問題一併交給 LLM，使模型依據資料作答並標示來源。

| 階段 | 時機 | 流程 |
|---|---|---|
| 建立索引 | 上傳文件時執行一次 | 文件 → 切段 → 嵌入模型將每段轉為向量 → 存入向量資料庫 |
| 問答 | 每次提問時執行 | 問題轉為向量 → 相似度檢索最相關的段落 → LLM 依段落與問題產生回答 → 附上引用來源 |

## 6.5.2 嵌入向量與相似度

嵌入模型將一段文字轉換為向量（`nomic-embed-text` 輸出 768 個數值）；語意相近的文字向量方向亦相近，故以向量的相似度（cosine similarity）找出最相關的段落。

```bash
ollama pull nomic-embed-text
curl http://localhost:11434/api/embed \
  -d '{"model": "nomic-embed-text", "input": "鍵盤遙控指令"}'
```

---

## 6.6 建立知識庫

**Step 1　設定嵌入模型**

```bash
ollama pull nomic-embed-text      # 若 6.5.2 已下載可略過
```

管理員控制台 → 設定 → 文件：「嵌入模型引擎」改為 **Ollama**，「嵌入模型」填入 `nomic-embed-text`，按儲存。

**Step 2　建立知識庫並上傳文件**

1. 左側「工作區」→「知識庫」→「＋」，填寫名稱（例如 `ch05`）與用途，按「建立知識」。
2. 點知識庫中的「＋」→「上傳檔案」，上傳第五章的 md 檔 [`ch05-ROS2模擬與範例指令.md`](../ch05/ch05-ROS2模擬與範例指令.md)。上傳後系統自動切段並建立向量索引。

> 上傳檔案時，檔案須在開啟網頁的那台電腦上：可在該電腦的瀏覽器開啟本課程的 GitHub 頁面，進入 `ch05` 資料夾下載此 md 檔。

**Step 3　於對話中使用知識庫**

開新對話，點輸入框左側的「＋」→「附加知識庫」選擇剛建立的知識庫（亦可在輸入框輸入 `#` 選擇），輸入框上方出現知識庫名稱後即可提問。回答下方的「來源」可點開，查看實際檢索到的段落。

> **注意**
> - 更換嵌入模型後，既有的知識庫須重新建立索引（刪除後重新上傳）；不同嵌入模型產生的向量無法互相比較。

## 6.6.1 結果對照

| 問題 | 未附加知識庫 | 附加知識庫 |
|---|---|---|
| 工作空間路徑 | ✗ 捏造的工作空間 | ✓ `~/tb3_ws/` |
| 鍵盤遙控指令 | ✗ 不存在的按鍵表 | ✓ `ros2 run turtlebot3_teleop teleop_keyboard` |
| 引用來源 | 無 | 標示 ch05 的 md 檔 |

## 6.6.2 檢索品質

教學機實測時，第一次提問只檢索到「安裝與編譯」的段落，路徑答對、遙控指令答錯；再問一次即全部答對。RAG 的效果取決於能否檢索到正確的段落。

| 方法 | 說明 |
|---|---|
| 拆分問題 | 一次只問一件事，使檢索結果集中 |
| 調整 Top K | 管理員控制台 → 設定 → 文件，增加每次檢索的段落數 |
| 降低溫度 | 減少生成的隨機性，使回答依循檢索到的段落 |
| 整理文件 | 每段落主題明確、標題清楚，有助於檢索 |

> **注意**
> - 問答時 LLM 與嵌入模型同時載入；上下文長度設為 8192 時 RAM 達 7.4／7.6 GB 並大量使用 SWAP，建議設為 4096（6.4.1）。

---

## 6.7 擴散模型

擴散模型於訓練時對圖片逐步加入雜訊，並訓練模型預測每一步加入的雜訊；生成時自純雜訊開始，依文字提示逐步去除雜訊。去雜訊的步數即「取樣步數」。

## 6.7.1 Stable Diffusion 的組成

Stable Diffusion 為潛在擴散模型：去雜訊不在 512×512 的圖片上進行，而在壓縮後的 64×64 潛在空間中進行，資料量約為原圖的 1／48。

| 元件 | 功能 |
|---|---|
| CLIP 文字編碼器 | 將提示詞轉為向量，引導去雜訊的方向；Stable Diffusion 1.5 僅支援英文 |
| U-Net | 每一步預測並去除潛在表示中的雜訊，運算量最大的部分 |
| VAE | 生成時將潛在表示還原為完整的圖片 |
| 取樣器（Sampler） | 決定每一步如何去除雜訊 |

## 6.7.2 生成參數

| 參數 | 作用 | 本章設定 |
|---|---|---|
| Prompt | 描述想要的畫面（英文） | `a small robot reading a book in a cozy library, digital art` |
| Negative prompt | 描述不想出現的內容，例如 `blurry, low quality` | 不填 |
| Sampling method | 取樣器 | DPM++ 2M（Schedule type：Karras） |
| Sampling steps | 去雜訊的步數；愈多愈精細、愈耗時 | 20 |
| CFG Scale | 圖片遵循提示詞的程度；過低則鬆散，過高則失真 | 7 |
| Seed | 決定初始雜訊；相同種子與參數可重現同一張圖 | 1234 |
| Width × Height | 圖片尺寸 | 512 × 512 |

---

## 6.8 jetson-containers

```bash
cd ~
git clone https://github.com/dusty-nv/jetson-containers
bash jetson-containers/install.sh
autotag stable-diffusion-webui
```

**正常輸出（教學機）**

```text
-- L4T_VERSION=36.5.0  JETPACK_VERSION=6.2.1  CUDA_VERSION=12.6
Found compatible container dustynv/stable-diffusion-webui:r36.4.0 (2025-04-22, 8.5GB)
```

| 指令 | 說明 |
|---|---|
| `install.sh` | 安裝相依套件，並建立 `jetson-containers`、`autotag` 指令 |
| `autotag <套件>` | 依 L4T 版本找出相容的映像檔名稱 |
| `jetson-containers run` | 加上 Jetson 所需的選項（GPU、資料夾）啟動容器 |

模型與生成的圖片存於 `~/jetson-containers/data`。

## 6.8.1 啟動 stable-diffusion-webui

**Step 1　先釋放記憶體**

```bash
ollama stop gemma3:4b && ollama stop nomic-embed-text
docker stop open-webui
free -h                  # available 應在 5 GB 以上
```

**Step 2　啟動容器**

```bash
cd ~/jetson-containers
jetson-containers run \
  -e PIP_INDEX_URL=https://pypi.org/simple \
  -e PIP_EXTRA_INDEX_URL=https://pypi.jetson-ai-lab.io/jp6/cu126 \
  $(autotag stable-diffusion-webui) \
  bash -c "cd /opt/stable-diffusion-webui && python3 launch.py \
    --data=/data/models/stable-diffusion --enable-insecure-extension-access \
    --opt-sdp-attention --skip-install --listen --port=7860"
```

Step 1 與 Step 2 亦可直接執行本資料夾的腳本：

```bash
bash ~/jetson-course/ch06/start_sd.sh
```

第一次執行時會詢問是否下載映像檔（輸入 `y`），並自動下載 Stable Diffusion 1.5 模型。出現 `Running on local URL: http://0.0.0.0:7860` 後，以瀏覽器開啟 `http://<Jetson IP>:7860`。結束時在終端機按 Ctrl＋C，再以 `docker start open-webui` 恢復 Open WebUI。

| 與原始啟動方式的差異 | 原因 |
|---|---|
| `PIP_INDEX_URL`、`PIP_EXTRA_INDEX_URL` | 容器內的套件來源為已停用的舊網址，啟動時安裝套件會失敗 |
| `--opt-sdp-attention` | 改用 PyTorch 內建的注意力運算，避開會使解碼失敗的 xFormers |
| `--skip-install` | 啟動時不再安裝套件，直接使用映像檔內的版本 |

## 6.8.2 生成圖片

1. 上方選擇模型 `v1-5-pruned-emaonly`。
2. 於 txt2img 分頁輸入提示詞，依 6.7.2 設定參數後按 Generate。
3. 生成時間與記憶體用量顯示於圖片下方；首次生成須載入模型，請以第二張的時間為準。

> **注意**
> - 畫面下方的「SDXL Styles」擴充功能預設勾選 Enable Style Selector，會自動修改提示詞，實驗時請取消勾選。

**教學機實測（512 × 512，DPM++ 2M Karras，Seed 1234）**

| 步數 | CFG | 生成時間 |
|---|---|---|
| 5 | 7 | 3.4 秒 |
| 20 | 7 | 10.3 秒 |
| 40 | 7 | 19.8 秒 |
| 40 | 2 | 19.6 秒 |
| 40 | 15 | 19.6 秒 |

每一步約 0.5 秒，生成時間與步數成正比，CFG 不影響時間；生成時記憶體約 6.9／7.6 GB，無法同時執行 LLM。

## 6.9 參數實驗

固定提示詞與 Seed 1234，分別改變下列參數：

| 實驗 | 設定 | 觀察 |
|---|---|---|
| 取樣步數（CFG 7） | 5 步 | 雜訊尚未去除完全，主體模糊、輪廓不清 |
| | 20 步 | 主體與背景皆已完整，為速度與品質的平衡點 |
| | 40 步 | 細節更多，但耗時加倍；超過一定步數後改善不明顯 |
| CFG Scale（40 步） | 2 | 受提示詞的約束弱，畫面雜亂、主題鬆散 |
| | 7 | 畫面完整且符合描述，為一般建議值 |
| | 15 | 過度遵循提示詞，色彩過飽和、對比強烈，構圖單調 |

---

## 常見問題

| 現象 | 原因 | 處理方式 |
|---|---|---|
| 安裝 Ollama 時出現 `PROTOCOL_ERROR` | 下載途中連線中斷 | 重新執行安裝指令；或於 `~/.curlrc` 加入 `--http1.1`（6.3.1） |
| `ollama ps` 的 PROCESSOR 不是 100% GPU | 記憶體不足，部分模型改由 CPU 執行 | 結束其他程式（Open WebUI 以外的瀏覽器、SD 容器）；`ollama stop` 其他模型 |
| Open WebUI 回覆 `does not support tools` | `gemma3:4b` 不支援工具呼叫，而內建工具預設開啟 | 關閉該模型的「內建工具」，「函式呼叫」維持預設（6.4.1） |
| Open WebUI 的模型清單是空的 | Open WebUI 連不到 Ollama | `systemctl status ollama` 確認服務執行中；確認 `docker run` 有 `--network=host` 與 `OLLAMA_BASE_URL` |
| 回答夾雜簡體字或大陸用語 | 模型的訓練資料以簡體中文為主 | 設定系統提示詞（6.4.1），或改用 `gemma3:4b` |
| 附加知識庫後仍答錯 | 未檢索到正確的段落 | 拆分問題、增加 Top K、降低溫度後再問（6.6.2）；查看「來源」 |
| 知識庫問答時系統變慢、大量使用 SWAP | 上下文長度過長 | 上下文長度改為 4096（6.4.1） |
| 啟動 SD 時 `Could not find a version that satisfies the requirement numpy==1.26.2` | 容器內的套件來源已停用 | 啟動時加上 `PIP_INDEX_URL`、`PIP_EXTRA_INDEX_URL`（6.8.1） |
| SD 取樣完成，最後一步出現 xFormers／`memory_efficient_attention` 錯誤 | xFormers 版本不支援 CUDA | 啟動時加上 `--opt-sdp-attention --skip-install`（6.8.1）；網頁設定中修改無效 |
| SD 生成到一半當機或極慢 | 記憶體不足 | 先停止 Ollama 模型與 Open WebUI（6.8.1 Step 1） |
| 生成的圖片與提示詞不符、風格被改變 | SDXL Styles 擴充功能自動修改提示詞 | 取消勾選 Enable Style Selector（6.8.2） |

```bash
# 確認目前佔用記憶體的程式
ollama ps
docker ps
free -h
tegrastats          # 按 Ctrl+C 結束
```
