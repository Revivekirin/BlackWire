````markdown
# 🕷️ Playwright Crawler Dashboard

<div align="center">
  <img src="./logo/1.png" alt="project-logo" width="300"/>
</div>

A Dockerized web crawler for **cyber threat intelligence** —  
collecting security news, dark web leaks, and enriching them with **MITRE ATT&CK mapping** and **LLM-based summarization**.

✅ **Tested on:** macOS (Apple Silicon, M2)  
⚠️ **You must create a `.env` file before running (see below)**

---

## ⚙️ Prerequisites: Environment Configuration

Before running any crawler or dashboard container,  
you **must create and configure `.env`** in the project root.

This `.env` file is automatically read by the `Settings` class:

```python
from settings import settings
print(settings.BASE_DOWNLOAD_DIR)
````

### 🧩 `.env` template

Copy the block below into a new file named `.env` at your project root:

```dotenv
# --- Base Paths (inside Docker containers) ---
BASE_DOWNLOAD_DIR=/app/downloads
ONION_LIST_PATH=/app/downloads/onion_list.json
BASE_NEWS_DIR=/app/downloads
OUTPUT_DIR=/app/data/shodan
CVEDB_PATH=/app/data/shodan/cvedb_shodan.csv
MITRE_XLSX_PATH=/app/data/mitre/enterprise-attack-v17.1.xlsx

# --- Network / Proxy ---
TOR_PROXY_ADDRESS=tor:9050
MAX_PAGES_PER_FQDN=5
CURL_CONNECT_TIMEOUT=20
CURL_MAX_TIME=60
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0

# --- API Keys ---
SHODAN_API_KEY=<your_shodan_api_key>
GEMINI_API_KEY=<your_google_gemini_api_key>
HF_TOKEN=<optional_huggingface_token>
```

If you are running on a **local host Tor** instead of Dockerized Tor:

```dotenv
TOR_PROXY_ADDRESS=host.docker.internal:9050
```

### 📁 Directory structure (recommended)

```
project-root/
│
├── .env
├── docker-compose.yml
├── settings.py
├── downloads/
│   ├── boannews/
│   ├── securityweek/
│   └── ...
│
├── data/
│   ├── shodan/
│   │   ├── shodan_data.csv
│   │   └── cvedb_shodan.csv
│   └── mitre/
│       └── enterprise-attack-v17.1.xlsx
│
├── scripts/
│   ├── run_compose.sh
│   ├── run_playwright.sh
│   ├── run_node.sh
│   └── run_extract.sh
│
└── visualization/
    └── app.py
```

---

## 🛠️ Initialization

```bash
# Run once before crawling
chmod +x ./scripts/init.sh
./scripts/init.sh
```

---

## 🌐 Dark Web Crawling

```bash
# Crawl onion sites through Tor proxy
chmod +x ./scripts/run_compose.sh
./scripts/run_compose.sh
```

---

## 💾 Info Extraction & MITRE Matching

```bash
# Extract leaked data, enrich CVEs, and map to MITRE ATT&CK
chmod +x ./scripts/run_extract.sh
./scripts/run_extract.sh
```

---

## 📰 News Crawling (Open Web)

```bash
# Node.js-based crawler
chmod +x ./scripts/run_node.sh
./scripts/run_node.sh

# Playwright-based crawler
chmod +x ./scripts/run_playwright.sh
./scripts/run_playwright.sh
```

> **Supported sources**:
> `gbhackers`, `security_affairs`, `thehackernews`, `securityweek`, `boannews`, `ransomwatch`

---

## 📊 Visualization & Dashboard

```bash
cd ./visualization
streamlit run app.py
```

Explore:

* Threat group clustering
* CVE–TTP (MITRE) matching
* Dark web activity summaries
* Gemini LLM–based report generation

---

## 📂 Output Directory

All crawled `.txt`, `.png`, and `.json` files will be saved under:

```
/app/downloads
```

For example:

```
downloads/
 ├── boannews/2025-11-09/article_1/
 │   ├── article.txt
 │   └── image_1.jpg
 └── securityweek/2025-11-09/article_3/
```

---

## 🧩 Stack Overview

| Component                            | Purpose                                 |
| ------------------------------------ | --------------------------------------- |
| **Playwright + Node.js**             | Crawling open web sources               |
| **Python (requests, BeautifulSoup)** | Parsing, CVE/SHODAN enrichment          |
| **Tor Proxy**                        | Access `.onion` darknet sites           |
| **MITRE ATT&CK Dataset**             | CVE–TTP mapping (enterprise v17.1)      |
| **Gemini API (LLM)**                 | Summarization and threat classification |
| **Streamlit**                        | Interactive visualization dashboard     |

---

## 🐳 Docker Compose Setup

### docker-compose.yml (example)

```yaml
services:
  tor:
    image: dperson/torproxy
    command: -a 'tor' -p '9050'
    ports:
      - "9050:9050"
    restart: unless-stopped

  crawler:
    build:
      context: .
      dockerfile: Dockerfile.crawler
    env_file: .env
    depends_on:
      - tor
    volumes:
      - ./downloads:/app/downloads
      - ./data:/app/data
    working_dir: /app
    tty: true

  viz:
    build:
      context: .
      dockerfile: Dockerfile.viz
    env_file: .env
    depends_on:
      - crawler
    volumes:
      - ./downloads:/app/downloads
      - ./data:/app/data
    working_dir: /app/visualization
    command: ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
    ports:
      - "8501:8501"
```

---

## 🧠 Notes

* **Tor proxy** (`tor:9050`) must be reachable inside Docker network.
* **.env** is loaded automatically by `pydantic.BaseSettings` in `settings.py`.
* If `.env` is missing, the code will fall back to defaults,
  but API calls (Shodan/Gemini) will fail without valid keys.
* Make sure to keep `.env` out of version control (`.gitignore`).

---

## 🧩 Example: Testing your config

```python
from settings import settings
print("Download dir:", settings.BASE_DOWNLOAD_DIR)
print("Tor proxy:", settings.TOR_PROXY_ADDRESS)
print("Shodan key loaded:", bool(settings.SHODAN_API_KEY))
```

Expected output:

```
Download dir: /app/downloads
Tor proxy: tor:9050
Shodan key loaded: True
```

---

## 📜 License & Contribution

MIT License.
Pull requests and issues are welcome!

---

## 📡 Summary

✅ `.env` file = central configuration hub
✅ Dockerized = reproducible, isolated crawling
✅ `settings.py` = automatic loader for all configs
✅ Works with both open web and dark web sources

> Build once, deploy anywhere — for robust cyber threat intelligence collection.
````