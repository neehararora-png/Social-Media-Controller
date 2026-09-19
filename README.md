# Social Media Controller & Multi-Channel Publisher

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Framework-Flask%203.x-green.svg)](https://palletsprojects.com/p/flask/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)
[![Platforms](https://img.shields.io/badge/Publishing-X%20%7C%20Instagram%20%7C%20Threads%20%7C%20Facebook%20%7C%20TikTok-orange.svg)](#supported-social-media-platforms)

An enterprise-grade, modular Python/Flask platform that unifies **real-time financial & cryptocurrency data scraping**, **automated vertical infographic generation**, **social media credential management**, and **multi-channel social media publishing** (Buffer-style cross-posting).

---

## Table of Contents

- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Social Media Upload & Publisher Engine](#social-media-upload--publisher-engine)
  - [Supported Platforms](#supported-social-media-platforms)
  - [Dual-Mode Engine: Simulation vs. Production](#dual-mode-engine-simulation-vs-production)
  - [Cross-Posting & Content Customization](#cross-posting--content-customization)
  - [Media Attachment & Dynamic Asset Browser](#media-attachment--dynamic-asset-browser)
  - [Scheduling & Drafts](#scheduling--drafts)
- [Quick Start Guide](#quick-start-guide)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Running the Application](#running-the-application)
- [Web Interface Overview](#web-interface-overview)
- [REST API Reference](#rest-api-reference)
- [Platform Credentials & Setup Guide](#platform-credentials--setup-guide)
- [Project Directory Structure](#project-directory-structure)
- [Programmatic Usage Example](#programmatic-usage-example)
- [Contributing & Collaborator Workflow](#contributing--collaborator-workflow)

---

## Key Features

- **🚀 Buffer-Style Multi-Channel Cross-Posting**: Compose once and dispatch across X (Twitter), Instagram Business, Meta Threads, Facebook Pages, and TikTok with a single click.
- **🛠️ Per-Platform Copy Tailoring**: Real-time character counters adhering to each platform's rules, plus expandable override fields to customize hashtags, handles, and copy per network.
- **🧪 Zero-Config Sandbox / Simulation Mode**: Built-in simulator allows testing your entire publishing workflow immediately without needing live API keys or developer accounts. Simulates realistic network delays, status responses, and clickable mock post permalinks.
- **🔐 Connection & Credential Profiles**: Group social accounts into reusable business profiles (e.g., "Crypto News Daily", "Brand X") with built-in credential verification.
- **📈 Live Market Data Scraping**: Scrapes top cryptocurrencies from CoinMarketCap, macroeconomic indicators & commodities from TradingEconomics, and market movers from Yahoo Finance.
- **🎨 Automated Infographic Builder**: Generates high-resolution 1080×1920 vertical market infographics (optimized for TikTok, Reels, and YouTube Shorts) using Pillow with cross-platform font fallbacks.
- **📜 Complete Audit Trail & History**: Tracks drafts, scheduled queues, and published posts with timestamps and per-account delivery statuses saved in `output/posts_history.json`.

---

## System Architecture

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
                                  |  - Normalizes numbers, dates, floats  |
                                  |  - Partitions into output/data/YYYY-MM|
                                  +-------------------+-------------------+
                                                      |
                                                      v
                                  +---------------------------------------+
                                  |            IMAGE BUILDER              |
                                  |  - PIL/Pillow Portrait (1080x1920)    |
                                  |  - Custom text, charts, and colors    |
                                  +-------------------+-------------------+
                                                      |
                                                      v
+---------------------------------------------------------------------------------------------------+
|                                  CENTRAL PUBLISHER MANAGER                                        |
|  - Strategy / Abstract Factory pattern dispatching to concrete platform publishers                |
|  - Resolves credentials via account profiles or environment variables                             |
|  - Drafts, scheduling, and posts history persistence (`output/posts_history.json`)                |
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

## Social Media Upload & Publisher Engine

The Social Media Upload module is located in `publisher/` and orchestrated by `publisher/manager.py`. It provides unified multi-platform publishing with native API support.

### Supported Social Media Platforms

| Platform | Protocol / API | Character Limit | Supported Media | Flow / Technical Implementation |
| :--- | :--- | :--- | :--- | :--- |
| **X (Twitter)** | Twitter API v2 + v1.1 | 280 chars | JPG, PNG, GIF, MP4 | OAuth 1.0a HMAC-SHA1 signer (`oauth_helper.py`), multipart media upload via `upload.twitter.com/1.1`, tweet creation via `POST /2/tweets`. |
| **Instagram** | Meta Graph API v20.0 | 2,200 chars | JPG, PNG, MP4 | Two-step Instagram Business Container flow (`POST /{ig_user_id}/media` followed by `POST /{ig_user_id}/media_publish`). |
| **Threads** | Meta Threads API v1.0 | 500 chars | Text, Images, MP4 | Two-step Threads Container flow (`POST /{threads_user_id}/threads` followed by `POST /{threads_user_id}/threads_publish`). |
| **Facebook Pages**| Meta Graph API v20.0 | 63,206 chars | Text, Images, Video | Direct feed publishing (`POST /{page_id}/feed` for text or `POST /{page_id}/photos` for images). |
| **TikTok** | TikTok Content Posting API v2 | 2,200 chars | MP4, Photos | Direct posting / photo-video init endpoint (`POST /v2/post/publish/creator_info/query/` & creator content upload). |

### Dual-Mode Engine: Simulation vs. Production

Every platform publisher implements dual-mode execution:
1. **Production Mode**: Triggered automatically when valid API credentials or tokens are configured (either via `.env` or in the Connection Handler UI). Real network requests are signed and transmitted to the official platform APIs.
2. **Sandbox / Simulation Mode**: Activated when credentials are empty or test tokens are supplied. 
   - Generates realistic mock IDs (e.g., `sim_tweet_982341`, `sim_ig_774921`).
   - Generates realistic mock permalinks (e.g., `https://twitter.com/i/web/status/sim_...`).
   - Emulates network latency (200–500ms) to mirror production conditions.
   - Allows teammates to develop and verify UI, scheduling, and post history workflows without access to production API keys.

### Cross-Posting & Content Customization

- **Unified Base Message**: Enter a single message that automatically populates across all active channels.
- **Dynamic Character Counters**: Real-time badges indicate characters used against individual platform maximums (e.g. 280 for X, 500 for Threads), warning you if limits are exceeded.
- **Network Overrides**: Click "Customize for [Network]" to override copy for specific channels (e.g., shorter text with hashtag punchlines for X, long-form discussion for Facebook).

### Media Attachment & Dynamic Asset Browser

- **Direct Upload**: Drag & drop or browse local image and video files (`.png`, `.jpg`, `.jpeg`, `.mp4`, `.webp`).
- **Asset Library Integration**: Browse and attach previously generated market infographics directly from the built-in asset picker (`/api/available-images`) with live thumbnail previews.

### Scheduling & Drafts

- **Publish Now**: Immediately dispatches the post to all selected accounts.
- **Schedule**: Pick a target date and time. Posts are staged in `output/posts_history.json` with status `"scheduled"`.
- **Save Draft**: Save unfinished copy and media combinations to revisit later.

---

## Quick Start Guide

### Prerequisites

- Python 3.10 or higher
- `pip` package manager
- (Optional) Git

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/neehararora-png/Social-Media-Controller.git
   cd Social-Media-Controller
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # On macOS / Linux:
   python3 -m venv .venv
   source .venv/bin/activate

   # On Windows:
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

Copy the sample environment file:
```bash
cp .env.example .env
```

Open `.env` in your text editor. If you do not have production API keys yet, you can leave the values blank — the controller will run seamlessly in **Sandbox / Simulation Mode**!

```env
# Flask Settings
FLASK_APP=main.py
PORT=5000

# X (Twitter) API
X_API_KEY=
X_API_SECRET=
X_ACCESS_TOKEN=
X_ACCESS_TOKEN_SECRET=
X_BEARER_TOKEN=

# Meta / Facebook Pages
FB_PAGE_ID=
FB_PAGE_ACCESS_TOKEN=

# Instagram Business
INSTAGRAM_ACCOUNT_ID=
INSTAGRAM_ACCESS_TOKEN=

# Meta Threads
THREADS_USER_ID=
THREADS_ACCESS_TOKEN=

# TikTok
TIKTOK_ACCESS_TOKEN=
TIKTOK_CLIENT_KEY=
```

### Running the Application

Launch the Flask server:
```bash
python main.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## Web Interface Overview

| Route | View | Description |
| :--- | :--- | :--- |
| **`/`** | **Landing Dashboard** | Main entry hub linking to all modules and documentation presentation. |
| **`/publish-work`** | **Social Media Upload & Composer** | Buffer-style multi-channel composer with live previews, character counters, overrides, scheduling, and post history. |
| **`/connection-handler`** | **Connection Handler** | Manage, validate, and store social platform accounts and API keys grouped into connection presets. |
| **`/image-builder`** | **Infographic Generator** | Generate customizable 1080×1920 market infographics from scraped crypto and financial data. |
| **`/index`** | **Scraper Pipeline** | Run end-to-end data scraping from CoinMarketCap, TradingEconomics, and Yahoo Finance. |
| **`/presentation`** | **Architecture Slides** | Interactive web slide deck detailing the system architecture and implementation. |

---

## REST API Reference

### Social Media Upload & Publishing

#### `POST /api/publish-work`
Publish, schedule, or draft a post across multiple social media channels.

**Content-Type**: `multipart/form-data`

**Parameters**:
- `content` *(string)*: Base post caption/text.
- `accounts` *(JSON string)*: Array of account objects to publish to:
  ```json
  [
    {"platform": "X (Twitter)", "account_name": "@CryptoDaily", "credentials": {}},
    {"platform": "Instagram", "account_name": "@cryptogram", "credentials": {}}
  ]
  ```
- `platform_customizations` *(JSON string, optional)*: Key-value map of platform-specific copy overrides:
  ```json
  {"X (Twitter)": "Short version with #BTC", "Facebook": "Detailed analysis..."}
  ```
- `files` *(file attachments, optional)*: One or more image or video files.
- `existing_media_paths` *(JSON string, optional)*: List of existing server file paths selected from asset library.
- `schedule_time` *(string, optional)*: ISO timestamp for scheduled delivery.
- `is_draft` *(string, optional)*: Set to `"1"` to save as a draft.

**Example Response**:
```json
{
  "success": true,
  "status": "published",
  "post_id": "9f323a7e-128a-4db5-b82b-0bb47b0a8eb7",
  "created_at": "2026-09-19T12:00:00.000000",
  "results": {
    "X (Twitter):@CryptoDaily": {
      "success": true,
      "post_id": "sim_tweet_1726744",
      "post_url": "https://twitter.com/i/web/status/sim_tweet_1726744",
      "platform": "X (Twitter)",
      "account_name": "@CryptoDaily",
      "message": "Tweet published successfully (Sandbox Mode)",
      "simulated": true
    }
  }
}
```

---

#### `GET /api/posts/history`
Retrieve past posts, drafts, and scheduled items.

**Query Parameters**:
- `status` *(optional)*: Filter by `"published"`, `"scheduled"`, or `"draft"`.

**Response**:
```json
{
  "history": [
    {
      "id": "uuid-here",
      "created_at": "2026-09-19T11:45:00.000000",
      "status": "published",
      "content": "Bitcoin hits new milestone!",
      "accounts": [...],
      "results": {...}
    }
  ]
}
```

---

#### `POST /api/connections/validate`
Validate API credentials for a given platform account.

**Request Body**:
```json
{
  "platform": "X (Twitter)",
  "account_name": "MyHandle",
  "credentials": {
    "api_key": "...",
    "api_secret": "...",
    "access_token": "...",
    "access_token_secret": "..."
  }
}
```

**Response**:
```json
{
  "valid": true,
  "simulated": false,
  "message": "Credentials verified with X API v2"
}
```

---

#### `GET /api/available-images`
Returns a list of generated graphics, scraped charts, and previously uploaded media ready for attaching to posts.

---

### Ingestion & Infographics

- `POST /api/run`: Executes end-to-end scraper pipeline and generates a daily snapshot JSON in `output/data/`.
- `POST /api/image-builder/generate`: Generates custom vertical infographics using Pillow.
- `GET /api/connections` & `POST /api/connections`: Get or save saved connection presets in `output/connections.json`.

---

## Platform Credentials & Setup Guide

### 1. X (formerly Twitter)
1. Navigate to the [X Developer Portal](https://developer.x.com/en/portal/dashboard).
2. Create a Project and an App.
3. Under **User authentication settings**, enable OAuth 1.0a and select **Read and Write** permissions.
4. Generate **API Key & Secret** (Consumer Keys) and **Access Token & Secret**.
5. Add keys to `.env` or in the Connection Handler UI.

### 2. Facebook Pages
1. Visit [Meta for Developers](https://developers.facebook.com) and create a Business App.
2. Add the **Facebook Login** or **Pages** product.
3. Obtain a Page Access Token with `pages_manage_posts` and `pages_read_engagement` scopes.
4. Set `FB_PAGE_ID` and `FB_PAGE_ACCESS_TOKEN`.

### 3. Instagram Business
1. Connect an Instagram Professional / Business account to your Facebook Page.
2. In Meta for Developers, request permissions `instagram_basic` and `instagram_content_publish`.
3. Get the Instagram Business Account ID via `GET /{page_id}?fields=instagram_business_account`.
4. Set `INSTAGRAM_ACCOUNT_ID` and `INSTAGRAM_ACCESS_TOKEN`.

### 4. Meta Threads
1. Register for the [Threads API](https://developers.facebook.com/docs/threads).
2. Authorize with scopes `threads_basic` and `threads_content_publish`.
3. Set `THREADS_USER_ID` and `THREADS_ACCESS_TOKEN`.

### 5. TikTok
1. Register a developer account at [TikTok for Developers](https://developers.tiktok.com).
2. Apply for the **Content Posting API**.
3. Set `TIKTOK_ACCESS_TOKEN` and `TIKTOK_CLIENT_KEY`.

---

## Project Directory Structure

```
Social-Media-Controller/
├── main.py                         # Main Flask application and REST routes
├── requirements.txt                # Python package dependencies
├── .env.example                    # Template environment variables
├── README.md                       # Repository documentation and guide
├── presentation.html               # Interactive visual architecture guide
│
├── publisher/                      # Social media upload & multi-channel subsystem
│   ├── __init__.py                 # Subsystem exports
│   ├── base.py                     # BasePublisher abstract class & PublishResult
│   ├── manager.py                  # Central orchestrator, history & dispatching
│   ├── oauth_helper.py             # Pure-Python RFC 3986 OAuth 1.0a HMAC-SHA1 signer
│   ├── x_publisher.py              # X (Twitter) API v2 and media upload v1.1
│   ├── facebook_publisher.py       # Facebook Graph API v20.0
│   ├── instagram_publisher.py      # Instagram Business 2-step Container API
│   ├── threads_publisher.py        # Meta Threads 2-step Container API
│   └── tiktok_publisher.py         # TikTok Content Posting API v2
│
├── scrapers/                       # Financial data web scrapers
│   ├── __init__.py
│   ├── coinmarketcap_scraper.py   # Crypto rankings & metrics scraper
│   ├── tradingeconomics_scraper.py # Macroeconomic indicators & commodities
│   └── yahoofinance_scraper.py     # Stocks, market movers & sentiment
│
├── image_generator/                # Infographic generation
│   ├── __init__.py
│   └── image_generator.py          # 1080x1920 portrait infographic generator
│
├── data_processor/                 # Data cleansing & partitioning
│   ├── __init__.py
│   └── data_processor.py           # Sanitization & date-partitioned JSON exporter
│
└── templates/                      # HTML5 web interfaces
    ├── landing.html                # App dashboard & module launcher
    ├── publish_work.html           # Buffer-style cross-posting composer
    ├── connection_handler.html     # Account credentials & connection profiles
    ├── image_builder.html          # Custom image asset builder
    ├── index.html                  # Scraper execution dashboard
    └── presentation.html           # Interactive architecture slides
```

---

## Programmatic Usage Example

You can use the publisher subsystem directly in your own Python scripts without launching the Flask web server:

```python
from publisher.manager import PublisherManager

# Initialize the manager
manager = PublisherManager()

# Define destination accounts
accounts = [
    {
        "platform": "X (Twitter)",
        "account_name": "@CryptoDaily",
        "credentials": {
            # Leave empty to run in Sandbox / Simulation Mode, or supply API keys:
            "api_key": "YOUR_KEY",
            "api_secret": "YOUR_SECRET",
            "access_token": "YOUR_TOKEN",
            "access_token_secret": "YOUR_TOKEN_SECRET"
        }
    },
    {
        "platform": "Instagram",
        "account_name": "@cryptogram",
        "credentials": {
            "account_id": "YOUR_IG_ACCOUNT_ID",
            "access_token": "YOUR_ACCESS_TOKEN"
        }
    }
]

# Publish simultaneously to all accounts
result = manager.publish_post(
    accounts=accounts,
    content="🚀 Bitcoin breaks key resistance level! Full breakdown below 👇",
    media_paths=["output/generated_images/tiktok/crypto_summary.png"],
    platform_customizations={
        "X (Twitter)": "🚀 #Bitcoin breaks resistance! #BTC #CryptoNews"
    }
)

print(f"Status: {result['status']}")
for target, res in result["results"].items():
    print(f"[{target}] Success: {res['success']} | URL: {res.get('post_url')}")
```

---

## Contributing & Collaborator Workflow

1. Fork or branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Set up your virtual environment and install dependencies.
3. Test changes locally. The sandbox mode guarantees you can verify changes to UI and backend dispatching without live credentials.
4. Verify byte-compilation:
   ```bash
   python -m py_compile main.py publisher/*.py scrapers/*.py
   ```
5. Commit and open a Pull Request!
