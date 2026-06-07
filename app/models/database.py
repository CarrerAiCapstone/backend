import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'careerpath.db')


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            description TEXT
        );
        
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            display_name TEXT,
            category TEXT,
            difficulty INTEGER
        );
        
        CREATE TABLE IF NOT EXISTS role_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_id INTEGER REFERENCES roles(id),
            skill_id INTEGER REFERENCES skills(id),
            importance REAL,
            step_order INTEGER,
            UNIQUE(role_id, skill_id)
        );
        
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            provider TEXT,
            url TEXT,
            skill_name TEXT,
            duration_hours REAL,
            rating REAL,
            level TEXT,
            is_free BOOLEAN
        );
        
        CREATE TABLE IF NOT EXISTS user_analyses (
            id TEXT PRIMARY KEY,
            user_name TEXT,
            role_id INTEGER REFERENCES roles(id),
            user_skills TEXT,
            readiness REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS career_levels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_id INTEGER REFERENCES roles(id),
            level_name TEXT NOT NULL,
            min_readiness REAL DEFAULT 0,
            description TEXT,
            additional_skills TEXT,
            salary_range TEXT,
            typical_years TEXT,
            UNIQUE(role_id, level_name)
        );
    ''')
    
    conn.commit()
    conn.close()


def populate_from_curated(curated_path='ml/data/curated_skills.json'):
    with open(curated_path, 'r') as f:
        data = json.load(f)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for role in data['roles']:
        cursor.execute(
            'INSERT OR IGNORE INTO roles (id, name, category, description) VALUES (?, ?, ?, ?)',
            (role['id'], role['name'], role['category'], role['description'])
        )
        
        for skill in role['skills']:
            cursor.execute(
                'INSERT OR IGNORE INTO skills (name, display_name, category, difficulty) VALUES (?, ?, ?, ?)',
                (skill['skill_name'], skill['display_name'], skill['category'], skill['difficulty'])
            )
            
            cursor.execute('SELECT id FROM skills WHERE name = ?', (skill['skill_name'],))
            skill_id = cursor.fetchone()['id']
            
            cursor.execute(
                'INSERT OR IGNORE INTO role_skills (role_id, skill_id, importance, step_order) VALUES (?, ?, ?, ?)',
                (role['id'], skill_id, skill['importance'], skill['step_order'])
            )
    
    conn.commit()
    conn.close()


def populate_courses(courses_path='data-science/mapping/courses.csv'):
    import csv
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    with open(courses_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute(
                'INSERT INTO courses (title, provider, url, skill_name, duration_hours, rating, level, is_free) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    row['title'],
                    row['provider'],
                    row['url'],
                    row['skill_name'],
                    float(row['duration_hours']),
                    float(row['rating']),
                    row['level'],
                    row['is_free'].lower() == 'true'
                )
            )
    
    conn.commit()
    conn.close()


def populate_career_levels():
    levels_data = {
        1: [
            {"level": "Junior", "min_readiness": 0, "desc": "Fokus pada analisis data terpandu, implementasi model sederhana", "skills": ["python", "sql", "statistics"], "salary": "Rp 5-10 juta", "years": "0-2 tahun"},
            {"level": "Mid", "min_readiness": 0.4, "desc": "Independen dalam analisis, memimpin proyek data kecil", "skills": ["machine_learning", "data_visualization", "cloud_aws"], "salary": "Rp 10-18 juta", "years": "2-4 tahun"},
            {"level": "Senior", "min_readiness": 0.7, "desc": "Arsitek solusi data, mentor junior, strategi data", "skills": ["deep_learning", "mlops", "leadership"], "salary": "Rp 18-30 juta", "years": "4+ tahun"},
        ],
        2: [
            {"level": "Junior", "min_readiness": 0, "desc": "Membangun komponen UI sederhana, memahami dasar web", "skills": ["html_css", "javascript", "git"], "salary": "Rp 4-8 juta", "years": "0-2 tahun"},
            {"level": "Mid", "min_readiness": 0.4, "desc": "Membangun aplikasi kompleks, optimalisasi performa", "skills": ["react", "typescript", "rest_api"], "salary": "Rp 8-15 juta", "years": "2-4 tahun"},
            {"level": "Senior", "min_readiness": 0.7, "desc": "Arsitek frontend, design system, performa & aksesibilitas", "skills": ["next_js", "testing", "leadership"], "salary": "Rp 15-25 juta", "years": "4+ tahun"},
        ],
        3: [
            {"level": "Junior", "min_readiness": 0, "desc": "Membangun API sederhana, memahami database", "skills": ["javascript", "sql", "git"], "salary": "Rp 5-9 juta", "years": "0-2 tahun"},
            {"level": "Mid", "min_readiness": 0.4, "desc": "Arsitek API, optimisasi query, caching", "skills": ["node_js", "postgresql", "docker"], "salary": "Rp 9-16 juta", "years": "2-4 tahun"},
            {"level": "Senior", "min_readiness": 0.7, "desc": "Microservices, system design, scalability", "skills": ["kubernetes", "cloud_aws", "leadership"], "salary": "Rp 16-28 juta", "years": "4+ tahun"},
        ],
        4: [
            {"level": "Junior", "min_readiness": 0, "desc": "Membuat laporan dasar, visualisasi sederhana", "skills": ["excel", "sql", "data_visualization"], "salary": "Rp 4-7 juta", "years": "0-2 tahun"},
            {"level": "Mid", "min_readiness": 0.4, "desc": "Analisis mandiri, dashboard interaktif, insight actionable", "skills": ["python", "power_bi", "statistics"], "salary": "Rp 7-12 juta", "years": "2-4 tahun"},
            {"level": "Senior", "min_readiness": 0.7, "desc": "Strategi data, mentorship, stakeholder management", "skills": ["machine_learning", "leadership", "business_intelligence"], "salary": "Rp 12-20 juta", "years": "4+ tahun"},
        ],
        5: [
            {"level": "Junior", "min_readiness": 0, "desc": "Mendesain wireframe, memahami dasar UX", "skills": ["ui_design", "figma", "html_css"], "salary": "Rp 4-8 juta", "years": "0-2 tahun"},
            {"level": "Mid", "min_readiness": 0.4, "desc": "Design system, user research, prototyping", "skills": ["ux_research", "prototyping", "visual_design"], "salary": "Rp 8-14 juta", "years": "2-4 tahun"},
            {"level": "Senior", "min_readiness": 0.7, "desc": "Design strategy, design ops, product thinking", "skills": ["design_thinking", "leadership", "product_strategy"], "salary": "Rp 14-22 juta", "years": "4+ tahun"},
        ],
        6: [
            {"level": "Junior", "min_readiness": 0, "desc": "Mengelola campaign sederhana, social media", "skills": ["digital_marketing", "content_marketing", "analytics"], "salary": "Rp 4-7 juta", "years": "0-2 tahun"},
            {"level": "Mid", "min_readiness": 0.4, "desc": "Strategi campaign, optimisasi budget, A/B testing", "skills": ["seo", "ppc", "marketing_analytics"], "salary": "Rp 7-12 juta", "years": "2-4 tahun"},
            {"level": "Senior", "min_readiness": 0.7, "desc": "Marketing strategy, team leadership, growth hacking", "skills": ["growth_strategy", "leadership", "brand_strategy"], "salary": "Rp 12-20 juta", "years": "4+ tahun"},
        ],
        7: [
            {"level": "Junior", "min_readiness": 0, "desc": "Membangun screen sederhana, memahami lifecycle", "skills": ["kotlin", "android", "git"], "salary": "Rp 5-10 juta", "years": "0-2 tahun"},
            {"level": "Mid", "min_readiness": 0.4, "desc": "App architecture, API integration, state management", "skills": ["rest_api", "firebase", "testing"], "salary": "Rp 10-18 juta", "years": "2-4 tahun"},
            {"level": "Senior", "min_readiness": 0.7, "desc": "Architecture decision, CI/CD, performance optimization", "skills": ["ci_cd", "architecture", "leadership"], "salary": "Rp 18-30 juta", "years": "4+ tahun"},
        ],
        8: [
            {"level": "Junior", "min_readiness": 0, "desc": "Mengelola server, memahami CI/CD dasar", "skills": ["linux", "git", "docker"], "salary": "Rp 6-12 juta", "years": "0-2 tahun"},
            {"level": "Mid", "min_readiness": 0.4, "desc": "Infrastructure as Code, monitoring, automation", "skills": ["kubernetes", "cloud_aws", "terraform"], "salary": "Rp 12-20 juta", "years": "2-4 tahun"},
            {"level": "Senior", "min_readiness": 0.7, "desc": "Architecture cloud, security, SRE practices", "skills": ["sre", "security", "leadership"], "salary": "Rp 20-35 juta", "years": "4+ tahun"},
        ],
        9: [
            {"level": "Junior", "min_readiness": 0, "desc": "Mendukung product owner, dokumentasi requirement", "skills": ["product_management", "agile", "communication"], "salary": "Rp 6-12 juta", "years": "0-2 tahun"},
            {"level": "Mid", "min_readiness": 0.4, "desc": "Memimpin produk sendiri, data-driven decision", "skills": ["data_analysis", "ux_research", "stakeholder_management"], "salary": "Rp 12-20 juta", "years": "2-4 tahun"},
            {"level": "Senior", "min_readiness": 0.7, "desc": "Product strategy, OKR, team leadership", "skills": ["product_strategy", "leadership", "business_development"], "salary": "Rp 20-35 juta", "years": "4+ tahun"},
        ],
        10: [
            {"level": "Junior", "min_readiness": 0, "desc": "Dokumentasi requirement, process mapping", "skills": ["data_analysis", "sql", "communication"], "salary": "Rp 5-9 juta", "years": "0-2 tahun"},
            {"level": "Mid", "min_readiness": 0.4, "desc": "Proses improvement, stakeholder management", "skills": ["business_intelligence", "process_mapping", "data_visualization"], "salary": "Rp 9-15 juta", "years": "2-4 tahun"},
            {"level": "Senior", "min_readiness": 0.7, "desc": "Business strategy, transformation lead", "skills": ["strategy", "leadership", "change_management"], "salary": "Rp 15-25 juta", "years": "4+ tahun"},
        ],
    }

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM career_levels')
    for role_id, levels in levels_data.items():
        for lvl in levels:
            cursor.execute(
                'INSERT INTO career_levels (role_id, level_name, min_readiness, description, additional_skills, salary_range, typical_years) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (role_id, lvl["level"], lvl["min_readiness"], lvl["desc"], json.dumps(lvl["skills"]), lvl["salary"], lvl["years"])
            )
    conn.commit()
    conn.close()


if __name__ == '__main__':
    init_db()
    populate_from_curated()
    populate_courses()
    populate_career_levels()
    print("Database initialized and populated.")
