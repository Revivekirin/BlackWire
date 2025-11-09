from pathlib import Path
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    BASE_DOWNLOAD_DIR: Path = Field(default=Path("/app/downloads"))
    ONION_LIST_PATH: Path = Field(default_factory=lambda: Path("/app/downloads/onion_list.json"))
    TOR_PROXY_ADDRESS: str = "127.0.0.1:9050"
    MAX_PAGES_PER_FQDN: int = 5
    CURL_CONNECT_TIMEOUT: int = 10
    CURL_MAX_TIME: int = 30
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0"
    SHODAN_API_KEY: str = ""
    MITRE_XLSX_PATH: str = ""
    CVEDB_PATH: str = ""
    BASE_NEWS_DIR: str = ""
    OUTPUT_DIR:str =""
    HF_TOKEN:str = ""
    GEMINI_API_KEY:str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
