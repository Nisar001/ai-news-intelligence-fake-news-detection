from fastapi import APIRouter

from app.api.v1.routes_analyze import router as analyze_router
from app.api.v1.routes_article import router as article_router
from app.api.v1.routes_health import router as health_router
from app.api.v1.routes_status import router as status_router
from app.api.v1.routes_summarize import router as summarize_router

router = APIRouter()
router.include_router(analyze_router, tags=["analysis"])
router.include_router(summarize_router, tags=["summarization"])
router.include_router(article_router, tags=["articles"])
router.include_router(status_router, tags=["jobs"])
router.include_router(health_router, tags=["health"])
