from fastapi import FastAPI, HTTPException
from supabase import create_client
from dotenv import load_dotenv
import os
from datetime import datetime

# загрузка переменных окружения
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL или SUPABASE_KEY не заданы в .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="French Trainer API")


@app.get("/")
def health():
    return {"status": "ok"}


@app.get("/next_phrase")
def next_phrase():
    """
    Возвращает следующую неотработанную фразу
    и увеличивает attempts
    """
    res = (
        supabase
        .table("phrases")
        .select("id, phrase_rf, attempts")
        .eq("status", "new")
        .order("id")
        .limit(1)
        .execute()
    )

    if not res.data:
        return {"message": "Нет новых фраз"}

    phrase = res.data[0]

    # обновляем attempts и last_used
    supabase.table("phrases").update({
        "attempts": phrase["attempts"] + 1,
        "last_used": datetime.utcnow().isoformat()
    }).eq("id", phrase["id"]).execute()

    return {
        "id": phrase["id"],
        "phrase_fr": phrase["phrase_rf"]
    }
from pydantic import BaseModel


class TaskRequest(BaseModel):
    phrase_id: int


@app.post("/task")
def create_task(data: TaskRequest):
    # получаем фразу по id
    res = (
        supabase
        .table("phrases")
        .select("id, phrase_rf")
        .eq("id", data.phrase_id)
        .limit(1)
        .execute()
    )

    if not res.data:
        raise HTTPException(status_code=404, detail="Фраза не найдена")

    phrase = res.data[0]["phrase_rf"]

    # формируем задание (ПОКА ПРОСТОЕ)
    task_text = (
        "Скажи по-французски, используя данную конструкцию:\n\n"
        f"«{phrase}»\n\n"
        "Составь полное предложение."
    )

    return {
        "phrase_id": data.phrase_id,
        "task": task_text
    }
from pydantic import BaseModel
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")


class AnswerRequest(BaseModel):
    phrase_id: int
    user_answer: str


@app.post("/answer")
def check_answer(data: AnswerRequest):
    # получаем исходную фразу
    res = (
        supabase
        .table("phrases")
        .select("phrase_rf")
        .eq("id", data.phrase_id)
        .limit(1)
        .execute()
    )

    if not res.data:
        raise HTTPException(status_code=404, detail="Фраза не найдена")

    phrase = res.data[0]["phrase_rf"]

    prompt = f"""
Ты — преподаватель французского языка.

Исходная конструкция:
{phrase}

Ответ ученика:
{data.user_answer}

Сделай проверку по правилам:
1) сначала дай перевод ответа на русский
2) скажи, корректна ли фраза
3) если есть ошибка — дай правильный вариант
4) сделай полный разбор глаголов и ключевых слов
5) добавь устойчивые выражения и примеры

Пиши по-русски.
"""

    completion = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Ты строгий и точный преподаватель французского."},
            {"role": "user", "content": prompt}
        ]
    )

    analysis = completion.choices[0].message.content

    return {
        "phrase_id": data.phrase_id,
        "analysis": analysis
    }
from pydantic import BaseModel

class AnalyzeRequest(BaseModel):
    phrase_id: int
    answer: str

class AnalyzeResponse(BaseModel):
    analysis: str

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    # ВРЕМЕННО: заглушка (позже подключим ИИ)
    analysis = (
        "Перевод: ...\n"
        "Фраза корректна / некорректна\n"
        "Разбор: ...\n"
        "Примеры: ..."
    )
    return {"analysis": analysis}

