## Agent OpenAI

### Описание
API-посредник между клиентом и OpenAI для простоты интеграции. 
Можно делать запросы к языковым моделям, создавать отдельные чаты 
и оплачивать расходы на использование.

### Установка и запуск
1. Склонируйте репозиторий
```bash
git clone https://github.com/KIvanX/AgentOpenAI
```

2. Установите зависимости
```bash
pip install -r requirements.txt
```

3. Создайте файл `.env` и добавьте в него переменные окружения
```env
DATABASE_URL=postgresql://user:password@0.0.0.0:5432/agent_openai
OPENAI_API_KEY=<API ключ OpenAI>
UKASSA_SHOP_ID=<SHOP_ID магазина для пополнения баланса>
UKASSA_SECRET_KEY=<SECRET_KEY магазина для пополнения баланса>
MODEL_NAME=gpt-4.1
PROMPT_PRICE=3.75
COMPLETION_PRICE=15
COMMISSION=<Коммиссия за использования (если есть)>
```

4. Создайте базу данных `agent_openai`
```SQL
CREATE DATABASE agent_openai;
```

5. Создайте файл `prompts.py` и добавьте в нее 
переменную `system_message` с системным сообщением языковой модели.
```prompts.py
system_message = '''Отвечай на вопросы клиента лакончино и вежливо.'''
```

6. Запустите проект
```bash
uvicorn main:app --port 5074 --reload
```