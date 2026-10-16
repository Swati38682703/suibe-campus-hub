"""Serve built browser routes without hiding missing API or asset paths."""
from pathlib import PurePosixPath
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        path = path.replace(chr(92), '/').lstrip('/')
        if any(part.startswith('.') for part in PurePosixPath(path).parts):
            raise HTTPException(status_code=404)
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            if error.status_code != 404 or path == 'api' or path.startswith(('api/', 'assets/')) or PurePosixPath(path).suffix:
                raise
            return await super().get_response('index.html', scope)
