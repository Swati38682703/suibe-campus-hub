import os
import tempfile
from pathlib import Path
import pytest

# Configure isolation before pytest imports any application modules.
task_tmp=tempfile.TemporaryDirectory()
os.environ['DATABASE_URL']='sqlite:///'+str(Path(task_tmp.name)/'test.db')
os.environ['APP_SECRET']='test-secret-only'
os.environ['ADMIN_TOKEN']='test-admin-only'
os.environ.pop('LLM_API_KEY',None)
from fastapi.testclient import TestClient
from backend.app.main import app,attempts
from backend.app.database import engine

@pytest.fixture(scope='session',autouse=True)
def dispose_database():
    assert Path(engine.url.database).resolve()==(Path(task_tmp.name)/'test.db').resolve()
    yield
    engine.dispose()
    task_tmp.cleanup()

@pytest.fixture
def client():
    attempts.clear()
    with TestClient(app) as c:
        yield c
