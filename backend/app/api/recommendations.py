from fastapi import APIRouter

router = APIRouter()


@router.post("/generate")
def generate_recommendation():
    return {
        "message": "Рекомендация сгенерирована",
        "data": {
            "calories": 2200,
            "meals": [
                "Овсянка с фруктами",
                "Курица с рисом",
                "Йогурт с орехами"
            ]
        }
    }