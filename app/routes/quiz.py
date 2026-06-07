from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import os
import random
from functools import lru_cache

router = APIRouter(prefix="/api/v1", tags=["quiz"])

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
QUESTIONS_PATH = os.path.join(DATA_DIR, 'questions.json')
METADATA_PATH = os.path.join(DATA_DIR, 'skill_metadata.json')


@lru_cache(maxsize=1)
def load_questions() -> dict:
    try:
        with open(QUESTIONS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


@lru_cache(maxsize=1)
def load_metadata() -> list:
    try:
        with open(METADATA_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def get_role_skills_from_metadata(role_id: int) -> list[str]:
    metadata = load_metadata()
    return list({item['skill_name'] for item in metadata if item['role_id'] == role_id})


def get_role_name_from_metadata(role_id: int) -> str | None:
    metadata = load_metadata()
    for item in metadata:
        if item['role_id'] == role_id:
            return item['role_name']
    return None


def get_skill_display_names(role_id: int) -> dict[str, str]:
    metadata = load_metadata()
    return {item['skill_name']: item['display_name']
            for item in metadata if item['role_id'] == role_id}


class QuizSubmitRequest(BaseModel):
    role_id: int
    answers: dict[str, int]


class SkillScore(BaseModel):
    skill_name: str
    display_name: str
    score: float
    mastered: bool


@router.get("/quiz/{role_id}")
def get_quiz(role_id: int):
    questions_data = load_questions()
    if not questions_data:
        raise HTTPException(
            status_code=503,
            detail="Data quiz belum siap ditampilkan sekarang. Coba lagi sebentar, ya."
        )

    role_skills = get_role_skills_from_metadata(role_id)
    role_name = get_role_name_from_metadata(role_id)

    if role_name is None:
        raise HTTPException(status_code=404, detail=f"Role dengan id {role_id} belum ditemukan.")

    display_names = get_skill_display_names(role_id)

    filtered_questions: list[dict] = []
    # Seed random for repeatability per user session if needed, but standard random is fine.
    # We choose exactly 1 question per skill.
    for skill_name in role_skills:
        if skill_name not in questions_data or not questions_data[skill_name]:
            continue
        # Select one random question for this skill
        q = random.choice(questions_data[skill_name])
        filtered_questions.append({
            "id": q["id"],
            "skill_name": skill_name,
            "display_name": display_names.get(skill_name, skill_name),
            "question": q["question"],
            "options": q["options"],
            "difficulty": q.get("difficulty", 1),
        })

    # Shuffle the overall question list so skills are mixed
    random.shuffle(filtered_questions)

    return {
        "role_id": role_id,
        "role_name": role_name,
        "total_questions": len(filtered_questions),
        "skills": role_skills,
        "questions": filtered_questions,
    }


@router.post("/quiz/submit")
def submit_quiz(request: QuizSubmitRequest):
    questions_data = load_questions()
    if not questions_data:
        raise HTTPException(
            status_code=503,
            detail="Data quiz belum siap diproses sekarang. Coba lagi sebentar, ya."
        )

    role_skills = get_role_skills_from_metadata(request.role_id)
    role_name = get_role_name_from_metadata(request.role_id)

    if role_name is None:
        raise HTTPException(status_code=404, detail=f"Role dengan id {request.role_id} belum ditemukan.")

    scores: dict[str, float] = {}
    total_correct = 0
    total_questions = 0

    for skill_name in role_skills:
        if skill_name not in questions_data:
            continue

        skill_questions = questions_data[skill_name]
        
        # Only evaluate questions that the user was actually asked and submitted answers for
        answered_in_skill = [q for q in skill_questions if q["id"] in request.answers]
        if not answered_in_skill:
            # If a user didn't receive any questions for this skill, default to 0
            scores[skill_name] = 0.0
            continue

        correct_count = 0
        for q in answered_in_skill:
            q_id = q["id"]
            if request.answers[q_id] == q["correct_index"]:
                correct_count += 1

        total_in_skill = len(answered_in_skill)
        total_questions += total_in_skill
        total_correct += correct_count

        score = (correct_count / total_in_skill * 100) if total_in_skill > 0 else 0.0
        scores[skill_name] = round(score, 1)

    total_score = (total_correct / total_questions * 100) if total_questions > 0 else 0.0
    mastered_skills = [skill for skill, score in scores.items() if score >= 60.0]

    return {
        "scores": scores,
        "mastered_skills": mastered_skills,
        "total_score": round(total_score, 1),
        "total_correct": total_correct,
        "total_questions": total_questions,
    }
