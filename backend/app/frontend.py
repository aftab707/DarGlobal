from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles
from starlette.types import Scope


class FrontendFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope):
        route_path = path.replace("\\", "/")
        can_fallback = (
            route_path != "api"
            and not route_path.startswith("api/")
            and not PurePosixPath(route_path).suffix
            and scope["method"] in ("GET", "HEAD")
        )
        try:
            response = await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404 or not can_fallback:
                raise
        else:
            if response.status_code != 404 or not can_fallback:
                return response
        return await super().get_response("index.html", scope)
from pathlib import PurePosixPath

