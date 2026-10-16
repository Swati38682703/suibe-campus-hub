import os
from pathlib import Path

def load_environment():
    path=Path(__file__).resolve().parents[2]/'.env'
    allowed={'ADMIN_TOKEN','APP_SECRET','DATABASE_URL','LLM_API_KEY','LLM_BASE_URL','LLM_MODEL'}
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            key,sep,value=line.partition('=')
            if sep and key in allowed and value.strip():
                os.environ.setdefault(key,value.strip())
