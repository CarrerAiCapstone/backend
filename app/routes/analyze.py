from fastapi import APIRouter
from pydantic import BaseModel, field_validator
from ..services.matching_engine import engine
from ..services.data_service import get_role_skills, get_courses_for_skills, get_career_levels, get_skill_explanations, get_career_insight_for_role, get_quick_win
import uuid

router = APIRouter(prefix="/api/v1", tags=["analysis"])


class AnalyzeRequest(BaseModel):
    role_id: int
    user_skills: list[str]
    user_name: str = "Pengguna"

    @field_validator('user_skills')
    @classmethod
    def validate_user_skills(cls, v):
        valid_skills = [s.strip() for s in v if s.strip()]
        return valid_skills


@router.post("/analyze")
def analyze_skills(request: AnalyzeRequest):
    role_skills = get_role_skills(request.role_id)
    if not role_skills:
        return {
            "status": "error",
            "code": "ROLE_NOT_FOUND",
            "message": "Role yang dipilih belum ditemukan.",
            "fallback_action": "Kembali ke daftar role",
        }

    try:
        analysis = engine.analyze_gaps(request.role_id, request.user_skills)
    except Exception as e:
        return {
            "status": "error",
            "code": "ANALYSIS_FAILED",
            "message": "Analisis belum berhasil dijalankan. Coba lagi sebentar, ya.",
            "fallback_action": "Periksa lagi skill yang dipilih lalu coba ulang",
            "detail": str(e),
        }

    if analysis.get('error'):
        return analysis['error']

    gap_skill_names = [g.get('skill_name', g.get('name', '')) for g in analysis.get('gaps', []) if g.get('skill_name', g.get('name'))]
    courses = get_courses_for_skills(gap_skill_names)
    explanations = get_skill_explanations(gap_skill_names, request.role_id)

    course_map = {}
    for course in courses:
        skill = course.pop('skill_name', None)
        if skill not in course_map:
            course_map[skill] = []
            course_map[skill].append(course)
        else:
            course_map[skill].append(course)

    learning_path = []
    for gap in analysis.get('gaps', []):
        skill_name = gap.get('skill_name', gap.get('name', ''))
        priority = "HIGH" if gap['importance'] >= 0.8 else "MEDIUM" if gap['importance'] >= 0.6 else "LOW"
        learning_path.append({
            'skill_name': skill_name,
            'display_name': gap['display_name'],
            'importance': gap['importance'],
            'step_order': gap['step_order'],
            'category': gap['category'],
            'priority': priority,
            'courses': course_map.get(skill_name, []),
            'explanation': explanations.get(skill_name, '')
        })

    matched_display = [
        {'name': m.get('skill_name', m.get('name', '')), 'display_name': m['display_name'], 'category': m['category']}
        for m in analysis.get('matched', [])
    ]

    analysis_id = str(uuid.uuid4())[:8]
    career_levels = get_career_levels(request.role_id, analysis['readiness'])
    current_level = None
    next_level = None
    for lvl in career_levels:
        if lvl['is_current_level']:
            current_level = lvl
        if lvl['is_next_level'] and not next_level:
            next_level = lvl
            
    quick_win = get_quick_win(gap_skill_names, request.role_id)
    
    response = {
        'analysis_id': analysis_id,
        'role_id': request.role_id,
        'readiness': analysis['readiness'],
        'matched_skills': matched_display,
        'gap_skills': [
            {
                'name': gap.get('skill_name', gap.get('name', '')),
                'display_name': gap.get('display_name', gap.get('skill_name', gap.get('name', ''))),
                'category': gap.get('category', ''),
                'importance': gap.get('importance', 0),
                'step_order': gap.get('step_order', 0),
            }
            for gap in analysis.get('gaps', [])
        ],
        'learning_path': learning_path,
        'quick_win': quick_win,
        'career_levels': career_levels,
        'current_level': current_level,
        'next_level': next_level,
    }

    if analysis.get('celebration'):
        response['celebration'] = analysis['celebration']

    if analysis.get('warning'):
        response['warning'] = analysis['warning']

    if analysis['readiness'] < 0.1:
        response['suggestion'] = "Mungkin ada role lain yang lebih dekat dengan modalmu saat ini."
        response['alternative_roles'] = True

    return response
