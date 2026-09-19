# Social Media Controller — Technical Implementation & Architecture Guide

## 1. Executive Summary

The **Social Media Controller** is an enterprise-grade, modular Python/Flask application that unifies market data scraping, automated visual content generation, social account connection management, and multi-channel publication (Buffer-style cross-posting).

The system addresses the end-to-end lifecycle of financial/crypto social media operations:
1. **Automated Ingestion**: Scrapes real-time cryptocurrency listings from CoinMarketCap, macroeconomic indicators and commodities from TradingEconomics, and market movers from Yahoo Finance.
2. **Data Normalization & Archiving**: Cleans and normalizes heterogeneous numeric data into structured, date-partitioned JSON snapshots.
3. **Automated Asset Generation**: Synthesizes high-resolution vertical infographics (1080×1920, TikTok/Reels/Shorts format) and accepts external AI-assisted image generation workflows.
4. **Connection & Credential Management**: Manages API keys, bearer tokens, and OAuth credentials grouped into logical connection profiles (e.g. "Crypto & Financial News Network").
5. **Unified Multi-Channel Dispatcher**: Cross-posts or schedules content simultaneously across **X (formerly Twitter)**, **Instagram**, **Threads**, **Facebook Pages**, and **TikTok**, handling per-platform character constraints, media requirements, and custom message tailoring.
6. **Dual-Mode Engine (Simulation vs. Production)**: Enables zero-friction local development and testing via a built-in sandbox simulator that mimics platform IDs, permalinks, and response structures without needing live credentials, while executing production API calls when credentials are provided.

---

## 2. High-Level Architecture & Data Flow

```
                                  +---------------------------------------+
                                  |            DATA INGESTION             |
                                  |  - CoinMarketCapScraper (v3 API)      |
                                  |  - TradingEconomicsScraper (HTML/BS4) |
                                  |  - YahooFinanceScraper (Quotes/BS4)   |
                                  +-------------------+-------------------+
                                                      |
                                                      v
                                  +---------------------------------------+
                                  |            DATA PROCESSOR             |
                                  |  - Normalizes floats & datetimes      |
                                  |  - Partitions into output/data/YYYY-MM|
                                  +-------------------+-------------------+
                                                      |
                                                      v
                                  +---------------------------------------+
                                  |            IMAGE BUILDER              |
                                  |  - PIL/Pillow Portrait Infographics   |
                                  |  - Custom Prompt / AI File Staging    |
                                  +-------------------+-------------------+
                                                      |
                                                      v
+---------------------------------------------------------------------------------------------------+
|                                  CENTRAL PUBLISHER MANAGER                                        |
|  - Validates credentials & accounts                                                               |
|  - Manages drafts, scheduling, and posts history (output/posts_history.json)                      |
|  - Routes to Platform-Specific Publishers (Abstract Factory / Strategy Pattern)                   |
+---------+--------------------+--------------------+--------------------+--------------------------+
          |                    |                    |                    |                          |
          v                    v                    v                    v                          v
  +---------------+    +---------------+    +---------------+    +---------------+    +-------------------+
  |  XPublisher   |    |  IGPublisher  |    |ThreadsPublish.|    |  FBPublisher  |    |  TikTokPublisher  |
  | API v1.1/v2   |    | Meta Graph    |    | Threads Graph |    | Meta Graph    |    | TikTok Posting v2 |
  | OAuth 1.0a    |    | Containers    |    | Containers    |    | Pages API     |    | Bearer Init       |
  +---------------+    +---------------+    +---------------+    +---------------+    +-------------------+
          |                    |                    |                    |                          |
          +--------------------+--------------------+--------------------+--------------------------+
                               |                    |
                               v                    v
                     [ LIVE APIS / WEB ]     [ SIMULATION SANDBOX ]
```

---

## 3. Directory & File Organization

```
Social-Media-Controller/
├── main.py                         # Flask application, routing, and controller endpoints
├── requirements.txt                # Python dependencies (Flask, requests, bs4, pillow)
├── data_processor/
│   ├── __init__.py
│   └── data_processor.py           # Sanitization, type conversion, date-based directory partitioning
├── scrapers/
│   ├── __init__.py
│   ├── coinmarketcap_scraper.py   # Scrapes top 30 crypto rankings and 24h market stats
│   ├── tradingeconomics_scraper.py # Scrapes key commodities and equity market indicators
│   └── yahoofinance_scraper.py     # Scrapes active stocks, gainers, losers, trending assets
├── image_generator/
│   ├── __init__.py
│   └── image_generator.py          # Generates 1080x1920 vertical market infographics using PIL
├── publisher/
│   ├── __init__.py
│   ├── base.py                     # BasePublisher abstract class & PublishResult dataclass
│   ├── manager.py                  # PublisherManager (orchestrator, history logger, dispatcher)
│   ├── oauth_helper.py             # Pure-Python RFC 3986 OAuth 1.0a HMAC-SHA1 signature builder
│   ├── x_publisher.py              # X (Twitter) API v2 and media upload v1.1
│   ├── facebook_publisher.py       # Facebook Graph API v20.0 (Feed & Photos)
│   ├── instagram_publisher.py      # Instagram Business Graph API v20.0 Container Flow
│   ├── threads_publisher.py        # Meta Threads API v1.0 Container Flow
│   └── tiktok_publisher.py         # TikTok Content Posting API v2
├── templates/
│   ├── landing.html                # App dashboard / module chooser
│   ├── index.html                  # Scraper and pipeline execution dashboard
│   ├── connection_handler.html     # Social account credential management & testing
│   ├── image_builder.html          # Custom image asset upload & builder
│   └── publish_work.html           # Buffer-style cross-posting composer & history dashboard
└── output/
    ├── connections.json            # Persistent credential and account preset storage
    ├── posts_history.json          # Complete audit log of all drafted, scheduled, and published posts
    ├── data/                       # Partitioned JSON data folders (e.g. YYYY-MM-DD/)
    ├── generated_images/           # Rendered visual content (e.g. tiktok/crypto_01_btc.png)
    └── uploads/                    # User-uploaded attachments and media
```

---

## 4. Subsystem Deep-Dive

### 4.1. Web Scraping Engine

The scraper subsystem extracts live market metrics from three distinct web properties:

#### A. `CoinMarketCapScraper` (`scrapers/coinmarketcap_scraper.py`)
- **Source**: CoinMarketCap Public Data API (`https://api.coinmarketcap.com/data-api/v3/cryptocurrency/listing`).
- **Mechanism**: Direct REST call with browser user-agent emulation.
- **Payload**: Extracts Top 30 cryptocurrencies sorted by market capitalization.
- **Fields Extracted**: `cmcRank`, `name`, `symbol`, `price` (USD), `percentChange24h`, and scrape timestamp.

#### B. `TradingEconomicsScraper` (`scrapers/tradingeconomics_scraper.py`)
- **Source**: TradingEconomics Commodities and Shares tables (`/commodities`, `/shares`).
- **Mechanism**: HTTP GET request with HTML parsing via `BeautifulSoup` (Soup table selection).
- **Target Commodities**: Crude Oil, Natural Gas, Coal, Propane, Gold, Silver, Copper, Steel, Lithium, Platinum, Lumber, Aluminum, Tin, Zinc, Nickel, Palladium.
- **Data Hygiene**: Strips commas, percentages, and string artifacts. Filters items by minimum price threshold (`price >= 1.00`).

#### C. `YahooFinanceScraper` (`scrapers/yahoofinance_scraper.py`)
- **Source**: Yahoo Finance market screener tabs (`most-active`, `trending_now`, `top_gainers`, `top_losers`).
- **Mechanism**: HTML parsing with dynamic table column indexing (`_find_index`) to handle table structure changes across regional Yahoo Finance mirrors.
- **Filtering**: Enforces positive price thresholds and formats numerical deltas.

---

### 4.2. Data Processing & Storage Pipeline

Implemented in `data_processor/data_processor.py`:
- **Date-Partitioned Architecture**: Automatically creates daily output folders: `output/data/<YYYY-MM-DD>/`.
- **Type Coercion**: Implements `_safe_float()` to ensure price, change percentage, market cap, and volume are safely converted to numeric types.
- **Snapshot Generation**: Creates consolidated snapshot files `data_YYYYMMDD_HHMMSS.json` alongside individual source files `coinmarketcap_top30_latest.json`, `tradingeconomics_required_latest.json`, and `yahoofinance_latest.json`.

---

### 4.3. Social Media Image Builder

Implemented in `image_generator/image_generator.py`:
- **Dimensions**: 1080 × 1920 pixels (9:16 aspect ratio optimized for TikTok, Instagram Reels, YouTube Shorts, and Threads photo posts).
- **Color Palette**: Modern dark theme `#0E0E18` background, `#8C52FF` accent top header, `#232332` footer, and dynamic price delta coloring (Emerald Green `#4CBE78` for gains, Crimson Red `#DC465F` for losses).
- **Rendering Elements**:
  1. Rank pill badge and crypto symbol.
  2. Asset full name and large formatted price.
  3. 24h percentage change with colored directional indicator.
  4. Market capitalization and 24h trading volume metrics.
  5. Timestamp and UTC freshness watermark.
- **Cross-Platform Font Fallbacks**: Searches for TrueType fonts across Windows (`segoeuib.ttf`, `arialbd.ttf`), macOS (`/System/Library/Fonts/Supplemental/Arial Bold.ttf`), and Linux (`DejaVuSans-Bold.ttf`).

---

### 4.4. Multi-Channel Publisher Subsystem

The publishing architecture utilizes the **Abstract Factory** and **Strategy** design patterns:

```
                      +-------------------+
                      |   BasePublisher   |
                      +---------+---------+
                                ^
         +----------------------+----------------------+
         |                      |                      |
+--------+--------+    +--------+--------+    +--------+--------+
|   XPublisher    |    |FacebookPublisher|    |InstagramPublish.|
+-----------------+    +-----------------+    +-----------------+
         |                      |                      |
+--------+--------+    +--------+--------+    +--------+--------+
| ThreadsPublisher|    | TikTokPublisher |    |_GenericPlatform.|
+-----------------+    +-----------------+    +-----------------+
```

#### Core Classes & Contracts:

1. **`PublishResult` (`publisher/base.py`)**:
   Standardized dataclass returned by all publishers:
   ```python
   @dataclass
   class PublishResult:
       platform: str
       account_name: str
       success: bool
       post_id: Optional[str] = None
       post_url: Optional[str] = None
       message: str = ""
       simulated: bool = False
       timestamp: str = ...
       raw_response: Optional[Dict[str, Any]] = None
   ```

2. **`BasePublisher` (`publisher/base.py`)**:
   Abstract base class requiring:
   - `validate_credentials() -> Dict[str, Any]`
   - `publish(content: str, media_paths: List[str], options: Dict) -> PublishResult`
   - `is_configured() -> bool`
   - Utility helpers: `_verify_media_exists()` and `_mask_secret()`

3. **`PublisherManager` (`publisher/manager.py`)**:
   - Central orchestrator handling platform name normalization (e.g. mapping `"twitter"`, `"x"`, `"X (Twitter)"` to the canonical factory).
   - Loads credentials from environment variables (`.env`) or incoming JSON payloads.
   - Dispatches posts across selected accounts concurrently.
   - Handles three operational execution modes:
     - **Draft Mode**: Persists post content, media, and selected accounts without publishing (`status: "draft"`).
     - **Scheduled Mode**: Saves intended dispatch time (`status: "scheduled"`).
     - **Immediate Publish**: Dispatches through active publishers and determines overall status: `published` (all passed), `partial_failure` (some passed), or `failed`.
   - Maintains audit logs in `output/posts_history.json`.

---

### 4.5. Platform API Protocols & Implementation Details

#### 1. X (formerly Twitter) Publisher (`publisher/x_publisher.py`)
- **Character Constraint**: 280 characters strict validation.
- **Authentication**: Pure Python OAuth 1.0a HMAC-SHA1 signing engine (`publisher/oauth_helper.py`). Generates RFC 3986 percent-encoded signature base strings and authorization headers without requiring heavyweight third-party libraries.
- **Media Upload Pipeline**:
  - Uploads images via Twitter API v1.1: `POST https://upload.twitter.com/1.1/media/upload.json`.
  - Obtains `media_id_string`.
- **Tweet Creation**:
  - Executes Twitter API v2: `POST https://api.twitter.com/2/tweets`.
  - Body: `{"text": content, "media": {"media_ids": [media_id]}}`.
  - Constructs permalink: `https://x.com/<handle>/status/<tweet_id>`.

#### 2. Facebook Pages Publisher (`publisher/facebook_publisher.py`)
- **Character Constraint**: 63,206 characters.
- **Authentication**: Meta Graph API v20.0 with Page Access Token.
- **Validation**: Queries `GET https://graph.facebook.com/v20.0/{page_id}` for page verification.
- **Publishing**:
  - **With Media**: `POST https://graph.facebook.com/v20.0/{page_id}/photos` with multipart `source` image stream and `caption`.
  - **Text-Only**: `POST https://graph.facebook.com/v20.0/{page_id}/feed` with `message`.

#### 3. Instagram Business / Creator Publisher (`publisher/instagram_publisher.py`)
- **Character Constraint**: 2,200 characters.
- **Requirements**: Instagram requires media attachment (standalone text is disallowed).
- **Two-Phase Asynchronous Container Flow**:
  1. **Container Creation**: `POST https://graph.facebook.com/v20.0/{instagram_account_id}/media` with `image_url` and `caption`. Receives `creation_id`.
  2. **Publish Container**: `POST https://graph.facebook.com/v20.0/{instagram_account_id}/media_publish` with `creation_id`.
- **Permalink Generation**: Computes URL using standard shortcode format `https://www.instagram.com/p/{shortcode}/`.

#### 4. Meta Threads Publisher (`publisher/threads_publisher.py`)
- **Character Constraint**: 500 characters.
- **Authentication**: Threads Official API via `graph.threads.net/v1.0`.
- **Two-Phase Publishing**:
  1. **Container Creation**: `POST https://graph.threads.net/v1.0/{threads_user_id}/threads` with `media_type` (`"TEXT"` or `"IMAGE"`), `text`, and optional `image_url`.
  2. **Publish Container**: `POST https://graph.threads.net/v1.0/{threads_user_id}/threads_publish` with `creation_id`.

#### 5. TikTok Content Posting API v2 (`publisher/tiktok_publisher.py`)
- **Character Constraint**: 4,000 characters.
- **Requirements**: Video or photo content is mandatory.
- **Authentication**: Bearer token via `https://open.tiktokapis.com/v2/user/info/`.
- **Publishing Pipeline**:
  - Initializes upload via `POST https://open.tiktokapis.com/v2/post/publish/content/init/`.
  - Supports privacy settings (`PUBLIC_TO_EVERYONE`, `MUTUAL_FOLLOW_FRIENDS`, `SELF_ONLY`), comment settings, and duet/stitch controls.

---

### 4.6. The Dual-Mode Simulation Engine (Sandbox)

One of the key architectural highlights is the built-in **Simulation Engine**:
- **Why It Exists**: Testing social media pipelines against live APIs often leads to rate limits, unintentional live posts on production feeds, or blocks due to missing developer account approvals.
- **How It Works**:
  - Each publisher inspects `is_configured()`. If credentials are absent or incomplete, it seamlessly pivots to simulation mode.
  - Generates realistic platform IDs (e.g. 19-digit snowflake IDs for X, 17-digit numeric IDs for Threads/IG).
  - Emulates valid shortcodes and permalinks (e.g. `https://x.com/user/status/1896694935599354582`, `https://www.instagram.com/p/TxN5r_DOzBH/`).
  - Sets `simulated: true` in the output dictionary.
  - Appends full execution logs to `output/posts_history.json`.

---

## 5. Complete REST API Specification

| Route | Method | Purpose | Input Payload / Query | Output Schema |
|---|---|---|---|---|
| `/` | `GET` | Render Main Landing Page | None | HTML |
| `/dashboard` | `GET` | Render Scraper Dashboard | None | HTML |
| `/connection-handler` | `GET` | Render Account Management UI | None | HTML |
| `/image-builder` | `GET` | Render Image Studio | None | HTML |
| `/publish-work` | `GET` | Render Buffer-style Publisher | None | HTML |
| `/api/run` | `POST` | Execute End-to-End Pipeline | None | `{"counts": {...}, "files": {...}, "image": {...}}` |
| `/api/scrape/coinmarketcap` | `POST` | Scrape CoinMarketCap only | None | `{"counts": {"crypto": 30}, "files": {...}, "scraped_json": [...]}` |
| `/api/scrape/tradingeconomics` | `POST` | Scrape TradingEconomics only | None | `{"counts": {...}, "files": {...}, "scraped_json": {...}}` |
| `/api/scrape/yahoofinance` | `POST` | Scrape Yahoo Finance tabs | None | `{"counts": {...}, "files": {...}, "scraped_json": {...}}` |
| `/api/image-generator` | `POST` | Generate Infographics from data | None | `{"counts": {"images_created": N}, "generated_images": [...]}` |
| `/api/connections` | `GET` | Retrieve saved connections | None | `{"connections": {"PresetName": {"accounts": [...]}}}` |
| `/api/connections` | `POST` | Save or update connection preset | `{"name": str, "original_name": str, "accounts": [...]}` | `{"success": true, "name": str}` |
| `/api/connections/<name>` | `DELETE` | Remove a connection preset | Path parameter: `name` | `{"success": true}` |
| `/api/connections/validate` | `POST` | Live test account credentials | `{"platform": str, "account_name": str, "credentials": {...}}` | `{"valid": bool, "simulated": bool, "message": str}` |
| `/api/available-images` | `GET` | List available media files | None | `{"images": [{"filename": str, "path": str, "size_bytes": int, ...}]}` |
| `/api/media/preview` | `GET` | Stream local image for preview | Query parameter: `?path=output/uploads/...` | Image binary (PNG/JPEG) |
| `/api/posts/history` | `GET` | Get post history & audit logs | Query parameter: `?status=published\|draft\|scheduled` | `{"history": [{"id": str, "status": str, "results": {...}}]}` |
| `/api/publish-work` | `POST` | Dispatch, schedule, or draft post | `multipart/form-data`: `connection_name`, `accounts`, `content`, `platform_customizations`, `schedule_time`, `is_draft`, `files` | `{"success": bool, "post_id": str, "status": str, "results": {...}}` |

---

## 6. How to Configure & Operate

### 6.1. Installation & Environment Setup

1. **Prerequisites**: Python 3.9+ and `pip`.
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Environment Configuration (Optional for Live Mode)**:
   Create a `.env` file in the root directory:
   ```env
   # X (Twitter) Credentials
   X_API_KEY=your_api_key
   X_API_SECRET=your_api_secret
   X_ACCESS_TOKEN=your_access_token
   X_ACCESS_TOKEN_SECRET=your_access_token_secret
   X_BEARER_TOKEN=your_bearer_token

   # Meta Facebook Page Credentials
   FB_PAGE_ID=100234567890123
   FB_PAGE_ACCESS_TOKEN=EAAG...your_token

   # Meta Instagram Business Credentials
   INSTAGRAM_ACCOUNT_ID=17841400000000000
   INSTAGRAM_ACCESS_TOKEN=EAAG...your_token

   # Meta Threads Credentials
   THREADS_USER_ID=1234567890
   THREADS_ACCESS_TOKEN=TH...your_token

   # TikTok Credentials
   TIKTOK_CLIENT_KEY=your_client_key
   TIKTOK_CLIENT_SECRET=your_client_secret
   TIKTOK_ACCESS_TOKEN=act.your_token
   ```

4. **Launch the Controller**:
   ```bash
   python3 main.py
   ```
   The application starts on `http://127.0.0.1:5000`.

---

### 6.2. User Workflow Guide

#### Step 1: Run Live Scrapes (`/dashboard`)
1. Open `http://127.0.0.1:5000/dashboard`.
2. Click **Run End-to-End** or trigger individual scrapers (CoinMarketCap, TradingEconomics, Yahoo Finance).
3. The dashboard displays scraped counts, JSON file paths, and generated infographics.

#### Step 2: Configure Channels & Accounts (`/connection-handler`)
1. Open `http://127.0.0.1:5000/connection-handler`.
2. Create a connection group (e.g. `"Market Updates Broadcast"`).
3. Add accounts across **X**, **Instagram**, **Threads**, **Facebook**, and **TikTok**.
4. Enter API credentials, or leave blank to utilize the sandbox simulation mode.
5. Click **Test & Validate** on each account to verify connectivity.

#### Step 3: Compose and Dispatch (`/publish-work`)
1. Open `http://127.0.0.1:5000/publish-work`.
2. Choose your active connection preset or click individual channel pills to target specific platforms.
3. Write your primary post text. The live character counters monitor limits for each selected platform simultaneously.
4. (Optional) Expand **Customize for Each Platform** to craft custom captions (e.g., concise 280-char copy with hashtags for X, narrative caption for Instagram).
5. Attach images:
   - Upload new files directly.
   - Or select previously generated market infographics via the **Choose Existing** media picker.
6. Execution Options:
   - **Publish Now**: Immediately dispatches the post across all channels.
   - **Schedule Post**: Pick a future date and time.
   - **Save as Draft**: Store post for later review.
7. Monitor results in the **Publish History** tab, including direct clickable post URLs and per-platform status badges.

---

## 7. Security, Auditing & Best Practices

1. **Credential Masking**: The UI masks secret tokens (`_mask_secret`), displaying only the first 3 and last 3 characters.
2. **Path Traversal Protection**: The `/api/media/preview` endpoint enforces workspace boundary checks:
   ```python
   abs_target = os.path.abspath(path)
   workspace = os.path.abspath(".")
   if not abs_target.startswith(workspace):
       return jsonify({"error": "Forbidden"}), 403
   ```
3. **Audit Trail**: Every action (successful publish, partial failure, draft, or schedule) is recorded with full payload metadata in `output/posts_history.json`.

---

## 8. Extensibility: Adding a New Social Platform

To add support for a new platform (e.g., **LinkedIn** or **YouTube Community**):

1. **Create Publisher Class**: In `publisher/linkedin_publisher.py`:
   ```python
   from publisher.base import BasePublisher, PublishResult
   from typing import Dict, Any, List, Optional

   class LinkedInPublisher(BasePublisher):
       def __init__(self, account_name: str, credentials: Optional[Dict] = None):
           super().__init__("LinkedIn", account_name, credentials)
           self.access_token = self.credentials.get("access_token")

       def validate_credentials(self) -> Dict[str, Any]:
           if not self.access_token:
               return {"valid": True, "simulated": True, "message": "Sandbox active"}
           # Call LinkedIn /v2/userinfo
           ...

       def publish(self, content: str, media_paths: Optional[List[str]] = None, options: Optional[Dict] = None) -> PublishResult:
           if not self.access_token:
               return PublishResult("LinkedIn", self.account_name, True, post_id="li_123", simulated=True)
           # Call LinkedIn UGC post API
           ...
   ```
2. **Register in `PublisherManager`** (`publisher/manager.py`):
   - Add platform name normalization in `normalize_platform_name()`.
   - Instantiate `LinkedInPublisher` in `create_publisher()`.
3. **Add Tab & Fields in `templates/connection_handler.html`**:
   - Add LinkedIn tab button and credential inputs (Author URN, Access Token).
4. **Update Channel Selector in `templates/publish_work.html`**:
   - Add LinkedIn channel pill and 3,000-character counter.

---
*Document Version: 2.4.0 — Maintained by Engineering Team*
