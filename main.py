from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import asyncpg
from openai import AsyncOpenAI
import yookassa
import dotenv
import os

from prompts import system_message

dotenv.load_dotenv()

client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
app = FastAPI()

yookassa.Configuration.account_id = os.environ.get("UKASSA_SHOP_ID")
yookassa.Configuration.secret_key = os.environ.get("UKASSA_SECRET_KEY")


class Request(BaseModel):
    prompt: str
    chat: str


class TopUp(BaseModel):
    amount: float


class CheckTopUp(BaseModel):
    payment_id: str


@app.get("/request/")
async def generate_text(request: Request):
    try:
        conn = await asyncpg.connect(os.environ["DATABASE_URL"])
        balance = (await conn.fetch("SELECT value FROM balance WHERE id = 0"))[0][0]
        if not request.prompt:
            return {"status": "success", "response": "", "balance": balance}

        if balance < 1:
            return JSONResponse(status_code=400, content={"status": "error", "reason": "You need to top up your balance"})

        data = await conn.fetch("SELECT prompt, result FROM chats WHERE chat = $1 ORDER BY id", request.chat)
        messages = [{'role': 'user' if i == 0 else 'assistant', 'content': line[i]}
                    for line in data for i in range(2)]

        completion = await client.chat.completions.create(
            model=os.environ.get('MODEL_NAME', 'gpt-4.1'),
            messages=[{'role': 'system', 'content': system_message}] + messages + [{'role': 'user', 'content': request.prompt}],
        )

        answer = completion.choices[0].message.content
        prompt_price = completion.usage.prompt_tokens * float(os.environ.get('PROMPT_PRICE', 3.75))
        completion_price = completion.usage.completion_tokens * float(os.environ.get('COMPLETION_PRICE', 15))
        price = (prompt_price + completion_price) * 100 / 10 ** 6 * 1.166 * 1.05 * float(os.environ.get('COMMISSION', '1.5'))
        balance -= price

        await conn.execute("UPDATE balance SET value = $1 WHERE id = 0", balance)
        await conn.execute("INSERT INTO chats(chat, prompt, result, amount) VALUES($1, $2, $3, $4)",
                           request.chat, request.prompt, answer, price)
        await conn.close()

        return {"status": "success", "response": answer, "balance": balance}
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "reason": str(e)})


@app.get("/top_up/")
async def top_up_balance(request: TopUp):
    try:
        payment = yookassa.Payment.create({
            "amount": {"value": request.amount, "currency": "RUB"},
            "confirmation": {"type": "redirect", "return_url": "https://www.google.ru/"},
            "capture": True,
            "payment_method_data": {"type": "bank_card"},
            "description": f'Пополнение баланса на {request.amount} руб'
        })

        return {"status": "success", "payment_id": payment.id, "url": payment.confirmation.confirmation_url}
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "reason": str(e)})


@app.post("/top_up/")
async def top_up_balance(request: CheckTopUp):
    try:
        payment = yookassa.Payment.find_one(request.payment_id)

        if payment.status == 'succeeded':
            conn = await asyncpg.connect(os.environ["DATABASE_URL"])
            transactions = {l[0] for l in (await conn.fetch("SELECT payment_id FROM transactions"))}
            if payment.id in transactions:
                return JSONResponse(status_code=400, content={"status": "error", "reason": "The operation has already been processed"})

            balance = (await conn.fetch("SELECT value FROM balance WHERE id = 0"))[0][0] + float(payment.amount.value)
            await conn.execute("INSERT INTO transactions(payment_id) VALUES($1)", payment.id)
            await conn.execute("UPDATE balance SET value = $1 WHERE id = 0", balance)
            await conn.close()
            return {"status": "success", "balance": balance}
        return JSONResponse(status_code=400, content={"status": "error", "reason": "The payment has not been completed yet"})
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "reason": str(e)})
