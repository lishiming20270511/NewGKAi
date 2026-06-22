import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from api.database import engine
from api.redis_client import get_redis, close_redis
from api.routers import auth, schools, recommendation, qa, report, admin, crawler, one_time_links, report_snapshots


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()
    await close_redis()


app = FastAPI(
    title="AI高考志愿规划师",
    version="2.0.0",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://121.41.69.234",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "服务器内部错误，请稍后重试"},
    )


# ─── Routers ─────────────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(schools.router)
app.include_router(recommendation.router)
app.include_router(qa.router)
app.include_router(report.router)
app.include_router(admin.router)
app.include_router(crawler.router)
app.include_router(one_time_links.router)
app.include_router(report_snapshots.router)


# ─── Frontend ────────────────────────────────────────────────────────────────

_FRONTEND = os.path.join(os.path.dirname(__file__), "frontend")

@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(
        os.path.join(_FRONTEND, "index.html"),
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}
    )

@app.get("/admin", include_in_schema=False)
@app.get("/admin/", include_in_schema=False)
async def serve_admin_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin.html")

@app.get("/admin.html", include_in_schema=False)
async def serve_admin():
    return FileResponse(os.path.join(_FRONTEND, "admin.html"))

@app.get("/s", include_in_schema=False)
@app.get("/s.html", include_in_schema=False)
async def serve_student():
    return FileResponse(
        os.path.join(_FRONTEND, "s.html"),
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}
    )

@app.get("/chat.html", include_in_schema=False)
@app.get("/chat", include_in_schema=False)
async def serve_chat():
    return FileResponse(os.path.join(_FRONTEND, "chat.html"))

if os.path.isdir(_FRONTEND):
    app.mount("/static", StaticFiles(directory=_FRONTEND), name="static")


# ─── Health ──────────────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
async def health():
    mysql_ok = False
    redis_ok = False

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        mysql_ok = True
    except Exception:
        pass

    try:
        r = get_redis()
        await r.ping()
        redis_ok = True
    except Exception:
        pass

    overall = "ok" if (mysql_ok and redis_ok) else "degraded"
    return {
        "status": overall,
        "mysql": "ok" if mysql_ok else "error",
        "redis": "ok" if redis_ok else "error",
    }
