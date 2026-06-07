from fastapi import APIRouter
from pydantic import BaseModel, field_validator
from ..services.data_service import get_courses_for_skills

router = APIRouter(prefix="/api/v1", tags=["recommendations"])


class RecommendRequest(BaseModel):
    gap_skills: list[str]

    @field_validator('gap_skills')
    @classmethod
    def validate_gap_skills(cls, v):
        valid_skills = [s.strip() for s in v if s.strip()]
        if not valid_skills:
            raise ValueError(
                'Skill yang ingin dipelajari belum dipilih. Tambahkan minimal satu skill dulu.'
            )
        return valid_skills


@router.post("/recommend")
def recommend_courses(request: RecommendRequest):
    try:
        courses = get_courses_for_skills(request.gap_skills)
    except Exception:
        return {
            "status": "error",
            "code": "RECOMMENDATION_FAILED",
            "message": "Rekomendasi kursus belum berhasil dimuat. Coba lagi sebentar, ya.",
            "fallback_action": "Periksa koneksi lalu coba lagi",
            "learning_path": [],
        }

    if not courses:
        return {
            "status": "ok",
            "learning_path": [],
            "message": "Belum ada kursus yang tersedia untuk skill ini saat ini.",
            "fallback_action": "Coba skill lain atau cek lagi nanti",
        }

    course_map = {}
    for course in courses:
        skill = course.pop('skill_name', None)
        if skill not in course_map:
            course_map[skill] = []
        course_map[skill].append(course)

    learning_path = []
    for skill_name, skill_courses in course_map.items():
        learning_path.append({
            'skill_name': skill_name,
            'courses': skill_courses
        })

    return {"learning_path": learning_path}
