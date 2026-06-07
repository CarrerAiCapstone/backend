from ..models.database import get_db_connection
import json


def get_all_roles():
    conn = get_db_connection()
    roles = conn.execute('SELECT id, name, category, description FROM roles ORDER BY id').fetchall()
    conn.close()
    return [dict(r) for r in roles]


def get_role_by_id(role_id):
    conn = get_db_connection()
    role = conn.execute('SELECT id, name, category, description FROM roles WHERE id = ?', (role_id,)).fetchone()
    conn.close()
    return dict(role) if role else None


def get_role_skills(role_id):
    conn = get_db_connection()
    skills = conn.execute('''
        SELECT s.name, s.display_name, s.category, s.difficulty, 
               rs.importance, rs.step_order
        FROM role_skills rs
        JOIN skills s ON rs.skill_id = s.id
        WHERE rs.role_id = ?
        ORDER BY rs.step_order, rs.importance DESC
    ''', (role_id,)).fetchall()
    conn.close()
    return [dict(s) for s in skills]


def get_courses_for_skills(skill_names, limit_per_skill=3):
    conn = get_db_connection()
    courses = []
    for skill_name in skill_names:
        skill_courses = conn.execute('''
            SELECT title, provider, url, skill_name, duration_hours, rating, level, is_free
            FROM courses
            WHERE skill_name = ?
            ORDER BY rating DESC, duration_hours ASC
            LIMIT ?
        ''', (skill_name, limit_per_skill)).fetchall()
        courses.extend([dict(c) for c in skill_courses])
    conn.close()
    return courses


def get_quick_win(gap_skills, role_id):
    if not gap_skills:
        return None
    conn = get_db_connection()
    placeholders = ','.join('?' for _ in gap_skills)
    skills_data = conn.execute(f'''
        SELECT name, display_name, difficulty
        FROM skills
        WHERE name IN ({placeholders})
    ''', gap_skills).fetchall()
    
    quick_win = None
    best_score = float('inf')
    
    for s in skills_data:
        skill_name = s['name']
        course_info = conn.execute('''
            SELECT MIN(duration_hours) as min_duration
            FROM courses
            WHERE skill_name = ?
        ''', (skill_name,)).fetchone()
        
        duration = course_info['min_duration'] if course_info and course_info['min_duration'] is not None else 10.0
        # Rank score: difficulty * 100 + duration
        score = s['difficulty'] * 100 + duration
        if score < best_score:
            best_score = score
            total_skills_res = conn.execute('SELECT COUNT(*) as count FROM role_skills WHERE role_id = ?', (role_id,)).fetchone()
            total_skills = total_skills_res['count'] if total_skills_res else 10
            
            quick_win = {
                'skill_name': skill_name,
                'display_name': s['display_name'],
                'difficulty': s['difficulty'],
                'estimated_hours': round(duration, 1),
                'readiness_boost': round(1.0 / total_skills, 2) if total_skills > 0 else 0.1
            }
    conn.close()
    return quick_win


def get_alternative_roles(role_id, user_skills):
    conn = get_db_connection()
    all_roles = conn.execute('SELECT id, name FROM roles WHERE id != ?', (role_id,)).fetchall()
    
    alternatives = []
    for role in all_roles:
        role_skills = conn.execute('''
            SELECT s.name FROM role_skills rs
            JOIN skills s ON rs.skill_id = s.id
            WHERE rs.role_id = ?
        ''', (role['id'],)).fetchall()
        role_skill_names = {s['name'] for s in role_skills}
        
        user_skill_set = set(user_skills)
        match_count = len(role_skill_names.intersection(user_skill_set))
        match_score = match_count / len(role_skill_names) if role_skill_names else 0
        
        alternatives.append({
            'role_id': role['id'],
            'role_name': role['name'],
            'match_score': round(match_score, 2)
        })
    
    conn.close()
    alternatives.sort(key=lambda x: x['match_score'], reverse=True)
    return alternatives[:3]


def get_skill_explanations(skill_names, role_id=None):
    """
    Returns explanations for each skill based on:
    - Market demand data (from curated data)
    - Role requirement context
    - Difficulty and importance level
    """
    explanations = {
        "python": "Skill fundamental untuk Data Scientist. 87% lowongan Data Scientist di Indonesia mencantumkan Python. Rata-rata gaji lebih tinggi 25% bagi yang menguasai Python.",
        "sql": "Bahasa database paling dicari. Hampir semua lowongan data mewajibkan SQL. Skill yang paling sering muncul di job posting data roles.",
        "machine_learning": "Inti dari peran Data Scientist. 76% Data Scientist menggunakan ML setiap hari. Skill dengan pertumbuhan permintaan tertinggi (45% YoY).",
        "statistics": "Dasar pengambilan keputusan berbasis data. 68% lowongan Data Scientist membutuhkan pemahaman statistik. Membantu menghindari kesalahan analisis.",
        "data_visualization": "Kunci komunikasi insight. Data yang divisualisasikan 60% lebih mudah dipahami stakeholder. Membuat laporan lebih impactful.",
        "excel": "Standard tool di hampir semua perusahaan. 92% perusahaan di Indonesia menggunakan Excel. Skill yang paling sering diminta untuk entry-level.",
        "javascript": "Bahasa utama web development. Digunakan oleh 98% website di dunia. Skill paling dicari di bidang Frontend.",
        "react": "Framework frontend paling populer. 40% dari lowongan Frontend Developer mencantumkan React. Ekosistem yang besar dan stabil.",
        "node_js": "Runtime JavaScript untuk backend. Memungkinkan Full Stack JavaScript. Permintaan meningkat 32% dalam 2 tahun terakhir.",
        "html_css": "Dasar dari semua web development. Wajib dikuasai sebelum framework apapun. 100% lowongan Frontend Developer membutuhkan ini.",
        "typescript": "Superset JavaScript yang mencegah error. 60% developer React beralih ke TypeScript. Menurunkan bug produksi hingga 40%.",
        "docker": "Standard containerization di industri. 85% perusahaan tech menggunakan Docker. Skill wajib untuk DevOps Engineer.",
        "kubernetes": "Orchestrator container paling populer. Permintaan naik 200% dalam 3 tahun. Skill dengan gaji tertinggi di bidang infrastructure.",
        "git": "Version control standard industri. Wajib untuk kolaborasi tim. Setiap software engineer harus menguasai ini.",
        "cloud_aws": "Cloud provider terbesar (32% market share). 70% lowongan DevOps menyebut AWS. Skill cloud dengan ekosistem terlengkap.",
        "postgresql": "Relational database paling advanced. Mendukung query kompleks dan JSON. Pilihan utama untuk production-grade apps.",
        "mongodb": "NoSQL database paling populer. Cocok untuk aplikasi dengan data tidak terstruktur. Skill database dengan pertumbuhan tercepat.",
        "rest_api": "Arsitektur API standard. 90% aplikasi modern menggunakan REST. Fundamental untuk Backend Developer.",
        "api_design": "Kunci membangun API yang scalable. Membedakan junior vs senior developer. Best practice untuk microservices.",
        "ui_design": "Inti dari peran UI/UX Designer. Menentukan 75% user experience. Skill paling kritis untuk product adoption.",
        "ux_research": "Data-driven design decision. Mengurangi redesign cost hingga 50%. Membedakan designer biasa vs profesional.",
        "figma": "Tool design kolaboratif paling populer. 80% designer UI/UX menggunakan Figma. Standard industri untuk design handoff.",
        "digital_marketing": "Skill inti marketing modern. 72% perusahaan meningkatkan budget digital marketing. Pertumbuhan karir 20% per tahun.",
        "seo": "Organic traffic driver utama. 53% traffic website berasal dari search. Skill marketing dengan ROI tertinggi.",
        "content_marketing": "Fundamental strategi marketing modern. 3x lebih efektif dari iklan tradisional. Skill yang selalu dicari.",
        "kotlin": "Bahasa utama Android development. 60% developer Android beralih ke Kotlin. Standar resmi Google untuk Android.",
        "swift": "Bahasa utama iOS development. Dioptimalkan untuk performa Apple. Skill wajib untuk iOS Developer.",
        "android": "Platform mobile terbesar (72% market share). 3.5 miliar pengguna aktif. Peluang karir yang sangat luas.",
        "ios": "Platform mobile premium. User dengan spending power tinggi. Revenue per user 2x Android.",
        "firebase": "Backend-as-a-Service untuk mobile. Populer untuk MVP dan prototyping. Mengurangi development time hingga 60%.",
        "product_management": "Skill inti Product Manager. Menjembatani bisnis, tech, dan design. Gaji tertinggi di bidang non-engineering.",
        "agile": "Metodologi kerja standard tech. 87% perusahaan menggunakan Agile. Wajib untuk Product Manager.",
        "data_analysis": "Fundamental Data Analyst. Mengubah data mentah menjadi insight actionable. 40% perusahaan kesulitan cari data analyst.",
        "business_intelligence": "Jembatan data dengan keputusan bisnis. Tools seperti Power BI/Tableau. Permintaan naik 25% per tahun.",
        "communication": "Soft skill paling dicari. Disebut di 80% lowongan kerja. Membedakan performer biasa vs top performer.",
        "teamwork": "Kolaborasi kunci di lingkungan kerja modern. 75% pekerjaan membutuhkan teamwork. Skill tim paling dihargai.",
        "problem_solving": "Skill fundamental untuk semua peran tech. Diuji di hampir semua wawancara kerja. Indikator performa kerja tertinggi.",
    }
    result = {}
    for name in skill_names:
        key = name.lower().replace(' ', '_').replace('-', '_')
        result[name] = explanations.get(key, "Skill ini penting untuk mendukung kompetensi di bidang ini. Menguasainya akan meningkatkan daya saing kamu di pasar kerja.")
    return result


def get_career_insight_for_role(role_id):
    """Return career insight text for a role"""
    insights = {
        1: "Data Scientist adalah salah satu profesi dengan pertumbuhan tercepat (35% YoY). Gaji rata-rata di Indonesia: Rp 12-25 juta/bulan untuk level menengah.",
        2: "Frontend Developer adalah pintu masuk karir tech paling populer. 230.000+ lowongan per tahun di Indonesia dengan permintaan terus meningkat.",
        3: "Backend Developer adalah tulang punggung setiap aplikasi. Rata-rata gaji Rp 10-22 juta/bulan dengan permintaan tinggi di startup dan enterprise.",
        4: "Data Analyst adalah profesi dengan entry barrier paling rendah di bidang data. 150.000+ lowongan per tahun dengan pertumbuhan 25% YoY.",
        5: "UI/UX Designer sangat dicari seiring meningkatnya kesadaran akan pentingnya user experience. Gaji rata-rata Rp 8-18 juta/bulan.",
        6: "Digital Marketing adalah skill paling versatile — dibutuhkan di semua industri. Pertumbuhan karir 20% per tahun dengan peluang remote work yang luas.",
        7: "Mobile Developer sangat dicari dengan pertumbuhan aplikasi mobile yang pesat. Rata-rata gaji Rp 10-20 juta/bulan.",
        8: "DevOps Engineer adalah salah satu profesi dengan gaji tertinggi di tech. Permintaan naik 40% dalam 2 tahun terakhir. Gaji Rp 15-30 juta/bulan.",
        9: "Product Manager adalah peran strategis yang menjembatani bisnis dan teknologi. Gaji tertinggi di bidang non-engineering: Rp 15-35 juta/bulan.",
        10: "Business Analyst sangat penting untuk transformasi digital perusahaan. Permintaan stabil dengan gaji rata-rata Rp 10-20 juta/bulan.",
    }
    return insights.get(role_id, "")


def save_user_analysis(analysis_id, user_name, role_id, user_skills, readiness):
    try:
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO user_analyses (id, user_name, role_id, user_skills, readiness) VALUES (?, ?, ?, ?, ?)',
            (analysis_id, user_name, role_id, ','.join(user_skills), readiness)
        )
        conn.commit()
    except Exception:
        # Persisting analysis history is helpful, but it should never block the main analysis flow.
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_career_levels(role_id, readiness_score):
    conn = get_db_connection()
    levels = conn.execute('''
        SELECT level_name, min_readiness, description, additional_skills, salary_range, typical_years
        FROM career_levels
        WHERE role_id = ?
        ORDER BY min_readiness ASC
    ''', (role_id,)).fetchall()
    conn.close()

    result = []
    for level in levels:
        lvl = dict(level)
        lvl['additional_skills'] = json.loads(lvl['additional_skills'] or '[]')
        lvl['is_current_level'] = readiness_score >= lvl['min_readiness']
        lvl['is_next_level'] = False
        result.append(lvl)

    current_idx = -1
    for i, lvl in enumerate(result):
        if lvl['is_current_level']:
            current_idx = i

    if current_idx >= 0 and current_idx + 1 < len(result):
        result[current_idx + 1]['is_next_level'] = True

    return result
