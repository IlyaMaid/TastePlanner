from fastapi import FastAPI
from app.api import auth, users, recommendations
from app.core.config import settings
from app.core.database import Base, engine
from app.models import user, profile

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug
)

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(recommendations.router, prefix="/recommendations", tags=["Recommendations"])


@app.get("/")
def root():
    return {"message": f"{settings.app_name} is running"}