# CareerPath AI Backend

Backend service untuk CareerPath AI.

Service ini menangani:
- analisis kesiapan pengguna terhadap role target
- quiz dan evaluasi jawaban
- rekomendasi learning path
- penyajian data role, skill, dan alternatif role

## Tech Stack

- FastAPI
- SQLite
- Scikit-learn
- TensorFlow

## Menjalankan Secara Lokal

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

API docs tersedia di `http://localhost:8000/docs`.

## Catatan

Repo ini menyertakan file runtime yang memang dibutuhkan backend saat berjalan, termasuk model dan data pendukung.

