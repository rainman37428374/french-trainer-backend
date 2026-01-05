from fastapi import FastAPI, HTTPException
from supabase import create_client
from dotenv import load_dotenv
from pydantic import BaseModel
from openai import OpenAI
import os
import random

# --------------------
# ENV
# --------------------
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL или SUPABASE_KEY не заданы")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY не задан")

# --------------------
# CLIENTS
# --------------------
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# --------------------
# APP
# --------------------
app = FastAPI(title="French Trainer API")


@app.get("/")
def health():
    return {"status": "ok"}


# --------------------
# NEXT PHRASE
# --------------------
@app.get("/next_phrase")
def next_phrase():
    res = (
        supabase
        .table("phrases")
        .select("id, phrase_rf, attempts")
        .eq("status", "new")
        .execute()
    )

    data = res.data

    if not data:
        return {"message": "Нет новых фраз"}

    phrase = random.choice(data)

    return {
        "id": phrase["id"],
        "phrase_fr": phrase["phrase_rf"]
    }


# --------------------
# ANALYZE
# --------------------
class AnalyzeRequest(BaseModel):
    phrase_id: int
    answer: str


class AnalyzeResponse(BaseModel):
    analysis: str


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    # получаем исходную конструкцию
    res = (
        supabase
        .table("phrases")
        .select("phrase_rf")
        .eq("id", req.phrase_id)
        .limit(1)
        .execute()
    )

    if not res.data:
        raise HTTPException(status_code=404, detail="Фраза не найдена")

    phrase = res.data[0]["phrase_rf"]

    prompt = f"""
Ты — строгий и точный преподаватель французского языка.

Исходная конструкция:
{phrase}

Ответ ученика:
{req.answer}

Сделай разбор СТРОГО по структуре:

1) Перевод ответа на русский
2) Фраза корректна / некорректна
3) Если некорректна — правильный вариант
4) Краткий грамматический разбор (по делу)
5) 2 примера с той же конструкцией

Пиши кратко, без воды.
"""

    response = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "Ты преподаватель французского языка."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
    )

    analysis_text = response.choices[0].message.content.strip()

    return {"analysis": analysis_text}


class MarkDoneRequest(BaseModel):
    phrase_id: int
@app.post("/mark_done")
def mark_done(req: MarkDoneRequest):
    supabase \
        .table("phrases") \
        .update({"status": "done"}) \
        .eq("id", req.phrase_id) \
        .execute()

    return {"status": "ok"}


var showDialog by remember { mutableStateOf(false) }

Button(
    onClick = { showDialog = true },
    modifier = Modifier
        .fillMaxWidth()
        .padding(top = 8.dp)
) {
    Text("Добавить новую фразу")
}
if (showDialog) {
    AlertDialog(
        onDismissRequest = { showDialog = false },
        confirmButton = {
            Button(onClick = {
                scope.launch {
                    ApiClient.api.addPhrase(
                        AddPhraseRequest(input)
                    )
                    input = ""
                    showDialog = false
                }
            }) {
                Text("Добавить")
            }
        },
        dismissButton = {
            Button(onClick = { showDialog = false }) {
                Text("Отмена")
            }
        },
        title = { Text("Новая фраза") },
        text = {
            TextField(
                value = input,
                onValueChange = { input = it },
                placeholder = { Text("Фраза на французском") }
            )
        }
    )
}



class AddPhraseRequest(BaseModel):
    phrase_fr: str
@app.post("/add_phrase")
def add_phrase(req: AddPhraseRequest):
    if not req.phrase_fr.strip():
        raise HTTPException(status_code=400, detail="Пустая фраза")

    supabase.table("phrases").insert({
        "phrase_rf": req.phrase_fr,
        "status": "new",
        "attempts": 0
    }).execute()

    return {"status": "added"}



