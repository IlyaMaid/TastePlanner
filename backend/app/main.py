from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, recommendations, recipes, users
from app.core.config import settings
from app.models import profile, user

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(recipes.router, prefix="/recipes", tags=["Recipes"])
app.include_router(
    recommendations.router,
    prefix="/recommendations",
    tags=["Recommendations"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    field_errors: dict[str, str] = {}

    for error in exc.errors():
        location = error.get("loc", ())
        field_name = next(
            (
                str(item)
                for item in reversed(location)
                if item not in {"body", "query", "path"}
            ),
            "non_field_error",
        )
        if field_name not in field_errors:
            field_errors[field_name] = error.get("msg", "Некорректное значение")

    return JSONResponse(
        status_code=422,
        content={
            "detail": "Ошибка валидации",
            "errors": field_errors,
        },
    )


@app.get("/")
def root():
    return {"message": f"{settings.app_name} is running"}


@app.get("/health")
def health():
    return {"status": "ok"}
