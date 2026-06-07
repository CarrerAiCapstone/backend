from fastapi import APIRouter
from ..services.data_service import get_all_roles, get_role_by_id, get_role_skills, get_alternative_roles

router = APIRouter(prefix="/api/v1/roles", tags=["roles"])


@router.get("")
def list_roles():
    try:
        roles = get_all_roles()
    except Exception:
        return {
            "status": "error",
            "code": "DATABASE_ERROR",
            "message": "Daftar role belum berhasil dimuat. Coba lagi sebentar, ya.",
            "fallback_action": "Muat ulang halaman ini",
        }

    if not roles:
        return {
            "roles": [],
            "status": "ok",
            "message": "Data role belum tersedia saat ini.",
            "fallback_action": "Cek lagi nanti atau hubungi tim pengelola",
        }

    return {"roles": roles}


@router.get("/{role_id}")
def get_role(role_id: int):
    try:
        role = get_role_by_id(role_id)
    except Exception:
        return {
            "status": "error",
            "code": "DATABASE_ERROR",
            "message": "Detail role belum berhasil dimuat. Coba lagi sebentar, ya.",
            "fallback_action": "Muat ulang halaman ini",
        }

    if not role:
        return {
            "status": "error",
            "code": "ROLE_NOT_FOUND",
            "message": "Role yang kamu cari belum ditemukan.",
            "fallback_action": "Kembali ke daftar role",
        }
    return role


@router.get("/{role_id}/skills")
def get_role_skills_endpoint(role_id: int):
    try:
        skills = get_role_skills(role_id)
    except Exception:
        return {
            "status": "error",
            "code": "DATABASE_ERROR",
            "message": "Daftar skill untuk role ini belum berhasil dimuat. Coba lagi sebentar, ya.",
            "fallback_action": "Muat ulang halaman ini",
        }

    if not skills:
        return {
            "skills": [],
            "status": "ok",
            "message": "Role ini belum punya data skill yang bisa ditampilkan.",
            "fallback_action": "Pilih role lain dulu",
        }

    return {"skills": skills}


@router.get("/{role_id}/alternatives")
def get_alternatives(role_id: int, user_skills: str):
    skills = [s.strip() for s in user_skills.split(",") if s.strip()]

    if not skills:
        return {
            "alternatives": [],
            "status": "error",
            "code": "NO_SKILLS_PROVIDED",
            "message": "Belum ada skill yang bisa dibandingkan. Pilih minimal satu dulu, ya.",
            "fallback_action": "Lengkapi skill lebih dulu",
        }

    try:
        alternatives = get_alternative_roles(role_id, skills)
    except Exception:
        return {
            "status": "error",
            "code": "DATABASE_ERROR",
            "message": "Alternatif role belum berhasil dicari. Coba lagi sebentar, ya.",
            "fallback_action": "Muat ulang halaman ini",
        }

    return {"alternatives": alternatives}
