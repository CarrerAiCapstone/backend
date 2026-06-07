from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from .routes import roles, analyze, recommend, quiz
from .models.database import init_db, populate_from_curated, populate_courses, populate_career_levels
from .services.matching_engine import engine
from contextlib import asynccontextmanager
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB if not present
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'careerpath.db')
    if not os.path.exists(db_path):
        init_db()
        populate_from_curated()
        populate_courses()
        populate_career_levels()
    yield


app = FastAPI(title="CareerPath AI API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(roles.router)
app.include_router(analyze.router)
app.include_router(recommend.router)
app.include_router(quiz.router)


# ── Global Exception Handlers ────────────────────────────────────────────

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    fallback_map = {
        404: "Tampilkan daftar profesi yang tersedia",
        405: "Gunakan metode HTTP yang benar",
        422: "Periksa kembali data yang dikirim",
        500: "Muat ulang halaman atau coba lagi nanti",
    }
    code_map = {
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        422: "UNPROCESSABLE_ENTITY",
        500: "INTERNAL_ERROR",
    }
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "code": code_map.get(exc.status_code, "HTTP_ERROR"),
            "message": exc.detail if exc.detail else "Terjadi kesalahan pada server",
            "fallback_action": fallback_map.get(exc.status_code, "Coba lagi nanti"),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    field_names = []
    for err in errors:
        loc = err.get("loc", [])
        field = loc[-1] if loc else "unknown"
        field_names.append(str(field))

    display_fields = ", ".join(field_names) if field_names else "data"

    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "code": "VALIDATION_ERROR",
            "message": f"Data tidak valid: periksa {display_fields}",
            "fallback_action": "Periksa format data yang dikirim dan coba lagi",
            "details": errors,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "code": "INTERNAL_ERROR",
            "message": "Terjadi kesalahan internal server. Silakan coba lagi.",
            "fallback_action": "Muat ulang halaman atau hubungi dukungan",
        },
    )


@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok", 
        "model_loaded": engine.dl_model is not None
    }


@app.get("/")
def root():
    return {"message": "CareerPath AI API", "docs": "/docs"}
