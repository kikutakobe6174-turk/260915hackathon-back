from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.errors import register_exception_handlers
from app.routers import (
    answer_sheets,
    auth,
    bank,
    formats,
    lessons,
    llm,
    prerequisites,
    problems,
    schools,
    students,
    tests,
    textbooks,
    trends,
    units,
    worksheets,
)

settings = get_settings()

app = FastAPI(title="ひかり塾 定期テスト演習システム API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(schools.router)
app.include_router(textbooks.router)
app.include_router(formats.router)
app.include_router(units.router)
app.include_router(students.router)
app.include_router(tests.router)
app.include_router(trends.router)
app.include_router(prerequisites.router)
app.include_router(bank.router)
app.include_router(problems.router)
app.include_router(worksheets.router)
app.include_router(lessons.router)
app.include_router(answer_sheets.router)
app.include_router(llm.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
