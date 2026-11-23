"""Serve built browser routes without hiding missing API or asset paths."""
from pathlib import PurePosixPath
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles


def _isolate(response):
    # 浏览器端多线程 WASM 抠图需要跨域隔离（SharedArrayBuffer）；
    # 站点静态资源均为同源，COEP 用 credentialless 避免影响后续跨站资源。
    response.headers.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
    response.headers.setdefault('Cross-Origin-Embedder-Policy', 'credentialless')
    return response


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        path = path.replace(chr(92), '/').lstrip('/')
        if any(part.startswith('.') for part in PurePosixPath(path).parts):
            raise HTTPException(status_code=404)
        try:
            return _isolate(await super().get_response(path, scope))
        except HTTPException as error:
            if error.status_code != 404 or path == 'api' or path.startswith(('api/', 'assets/')) or PurePosixPath(path).suffix:
                raise
            return _isolate(await super().get_response('index.html', scope))
