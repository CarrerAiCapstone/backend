import json
import os
import pickle
import numpy as np
import scipy.sparse

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')


class MatchingEngine:
    
    def __init__(self):
        self.vectorizer = None
        self.tfidf_matrix = None
        self.skill_metadata = None
        self.synonyms = {}
        self.dl_model = None
        
        self._load_synonyms()
        self._load_tfidf_model()
        self._load_dl_model()
    
    def _load_synonyms(self):
        synonyms_path = os.path.join(DATA_DIR, 'synonyms.json')
        if os.path.exists(synonyms_path):
            with open(synonyms_path, 'r', encoding='utf-8') as f:
                self.synonyms = json.load(f)
    
    def _load_tfidf_model(self):
        vectorizer_path = os.path.join(DATA_DIR, 'tfidf_vectorizer.pkl')
        matrix_path = os.path.join(DATA_DIR, 'tfidf_matrix.npz')
        metadata_path = os.path.join(DATA_DIR, 'skill_metadata.json')
        
        if all(os.path.exists(p) for p in [vectorizer_path, matrix_path, metadata_path]):
            with open(vectorizer_path, 'rb') as f:
                self.vectorizer = pickle.load(f)
            self.tfidf_matrix = scipy.sparse.load_npz(matrix_path)
            with open(metadata_path, 'r', encoding='utf-8') as f:
                self.skill_metadata = json.load(f)

    def _load_dl_model(self):
        # The model is usually placed in ml/data/ or backend/model/
        model_paths = [
            os.path.join(DATA_DIR, '..', 'ml', 'data', 'skill_matcher.keras'),
            os.path.join(DATA_DIR, 'model', 'skill_matcher.keras'),
            os.path.join(DATA_DIR, '..', 'model', 'skill_matcher.keras')
        ]
        
        for path in model_paths:
            if os.path.exists(path):
                try:
                    import sys
                    project_root = os.path.abspath(os.path.join(DATA_DIR, '..', '..'))
                    if project_root not in sys.path:
                        sys.path.append(project_root)
                        
                    import tensorflow as tf
                    # Register custom layers
                    from ml.training.custom_layers import AttentionCosineSimilarity, GatedSimilarityFusion
                    
                    self.dl_model = tf.keras.models.load_model(
                        path,
                        custom_objects={
                            'AttentionCosineSimilarity': AttentionCosineSimilarity,
                            'GatedSimilarityFusion': GatedSimilarityFusion
                        },
                        safe_mode=False
                    )
                    print(f"Successfully loaded Deep Learning model from: {path}")
                    return
                except Exception as e:
                    print(f"Failed to load Deep Learning model from {path}: {e}")
        print("Warning: No Deep Learning model loaded. Using TF-IDF/synonym fallback.")
    
    def normalize_skills(self, user_skills):
        normalized = []
        for skill in user_skills:
            skill_lower = skill.lower().strip()
            for canonical, variants in self.synonyms.items():
                if skill_lower == canonical or skill_lower in variants:
                    normalized.append(canonical)
                    break
            else:
                normalized.append(skill_lower)
        return normalized
    
    def find_matches(self, user_skills):
        if self.vectorizer is None or self.tfidf_matrix is None:
            return self._fallback_match(user_skills)
        
        normalized = self.normalize_skills(user_skills)
        user_text = ' '.join(normalized)
        user_vector = self.vectorizer.transform([user_text])
        similarities = (user_vector @ self.tfidf_matrix.T).toarray().flatten()
        
        results = []
        for idx, sim_score in enumerate(similarities):
            meta = self.skill_metadata[idx] if self.skill_metadata else {}
            results.append({**meta, 'similarity_score': float(sim_score)})
        
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results
    
    def _fallback_match(self, user_skills):
        if not user_skills:
            return []
        normalized = self.normalize_skills(user_skills)
        results = []
        for meta in (self.skill_metadata or []):
            score = 1.0 if meta['skill_name'] in normalized else 0.0
            results.append({**meta, 'similarity_score': score})
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results
    
    def analyze_gaps(self, role_id, user_skills):
        normalized = self.normalize_skills(user_skills)
        role_skills = [m for m in (self.skill_metadata or []) if m['role_id'] == role_id]
        
        if not role_skills:
            return {
                'readiness': 0.0,
                'matched': [],
                'gaps': [],
                'error': {
                    'code': 'ROLE_NOT_FOUND',
                    'message': 'Profesi tidak ditemukan atau belum memiliki data skill',
                    'fallback_action': 'Pilih profesi lain dari daftar yang tersedia',
                    'suggestion': 'Coba profesi lain yang lebih sesuai',
                    'alternative_roles': True,
                }
            }
        
        if not normalized:
            return {
                'readiness': 0.0,
                'matched': [],
                'gaps': role_skills,
                'warning': {
                    'code': 'NO_SKILLS_PROVIDED',
                    'message': 'Tidak ada skill yang dipilih. Silakan pilih minimal satu skill yang kamu kuasai.',
                    'fallback_action': 'Pilih skill dari daftar yang tersedia',
                }
            }
        
        matched = []
        gaps = []
        
        for skill in role_skills:
            target_name = skill['skill_name']
            
            # 1. Exact or synonym match (Fast path)
            if target_name in normalized:
                matched.append(skill)
                continue
            
            # 2. Deep Learning semantic match (Slow/Smart path)
            is_matched = False
            if self.dl_model is not None and self.vectorizer is not None:
                try:
                    import tensorflow as tf
                    # Vectorize target skill (1, 1522)
                    target_vector = self.vectorizer.transform([target_name]).toarray().astype(np.float32)
                    
                    # Compare with each user skill
                    for u_skill in normalized:
                        user_vector = self.vectorizer.transform([u_skill]).toarray().astype(np.float32)
                        
                        # Siamese model prediction
                        score = float(self.dl_model([user_vector, target_vector], training=False).numpy()[0][0])
                        
                        # If model outputs high confidence similarity, count as match
                        if score >= 0.75:
                            is_matched = True
                            break
                except Exception as e:
                    # Silent fallback if Keras/TF errors out
                    pass
            
            if is_matched:
                matched.append(skill)
            else:
                gaps.append(skill)
        
        gaps.sort(key=lambda x: x['importance'], reverse=True)
        
        readiness = len(matched) / len(role_skills) if role_skills else 0
        
        result = {
            'readiness': round(readiness, 2),
            'matched': matched,
            'gaps': gaps
        }
        
        # Merge/Relocate all celebration and warning logic properly
        if len(matched) == len(role_skills) or readiness >= 1.0:
            result['celebration'] = {
                'message': 'Selamat! Kamu sudah menguasai semua skill yang dibutuhkan untuk profesi ini! 🎉',
                'action': 'Kamu siap melamar posisi ini atau lanjut ke level berikutnya',
            }
        elif readiness < 0.1:
            result['warning'] = {
                'code': 'LOW_READINESS',
                'message': 'Kesiapanmu sangat rendah untuk profesi ini',
                'suggestion': 'Coba profesi lain yang lebih sesuai dengan skill yang kamu miliki',
                'alternative_roles': True,
            }
        elif readiness < 0.3:
            result['warning'] = {
                'code': 'LOW_READINESS',
                'message': 'Kesiapanmu masih rendah untuk profesi ini. Fokus pada skill prioritas HIGH terlebih dahulu.',
                'suggestion': 'Tingkatkan skill utama sebelum melamar.',
            }
        
        return result


engine = MatchingEngine()
