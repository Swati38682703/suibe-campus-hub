"""Cloud entry point: keep API and the built React website on one origin."""
import os
from .database_url import normalize_database_url

if not os.getenv('APP_SECRET'):
    raise RuntimeError('Set a persistent APP_SECRET in the hosting environment')
if not normalize_database_url(os.getenv('DATABASE_URL', '')).startswith('postgresql+psycopg://'):
    raise RuntimeError('Cloud deployment requires a persistent PostgreSQL DATABASE_URL')

from .main import app
from .database import ROOT
from .spa import SPAStaticFiles

app.mount('/', SPAStaticFiles(directory=ROOT / 'frontend' / 'dist', html=True), name='website')
