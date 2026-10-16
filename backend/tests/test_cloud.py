from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.app.spa import SPAStaticFiles
from backend.app.database_url import normalize_database_url


def test_provider_urls_use_installed_driver():
    for scheme in ('postgresql://','postgres://'):
        assert normalize_database_url(scheme+'user:password@host/db?sslmode=require') == 'postgresql+psycopg://user:password@host/db?sslmode=require'
    for url in ('sqlite:///local.db','postgresql+psycopg://user:password@host/db'):
        assert normalize_database_url(url) == url


def test_cloud_frontend_routes_and_missing_resources(tmp_path):
    (tmp_path/'index.html').write_text('<html>campus frontend</html>',encoding='utf-8')
    (tmp_path/'assets').mkdir()
    (tmp_path/'assets'/'app.js').write_text('console.log("campus")',encoding='utf-8')
    app=FastAPI()
    @app.get('/api/health')
    def health(): return {'status':'ok'}
    app.mount('/',SPAStaticFiles(directory=tmp_path,html=True))
    with TestClient(app) as client:
        for url in ('/','/competitions','/dining','/rooms/A101'):
            response=client.get(url)
            assert response.status_code==200 and 'campus frontend' in response.text
        assert client.get('/assets/app.js').status_code==200
        assert client.get('/api/health').json()=={'status':'ok'}
        for url in ('/api/missing','/assets/missing','/missing.png','/.env','/%2e%2e/.local-secret'):
            assert client.get(url).status_code==404
        assert client.post('/competitions').status_code==405
