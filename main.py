# from openai import OpenAI
from fastapi import FastAPI, Form, Request, WebSocket
from typing import Annotated
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import os
from dotenv import load_dotenv

load_dotenv()

# openai = OpenAI(
#     api_key = os.getenv('OPENAI_API_SECRET_KEY')
# )

app = FastAPI()

templates = Jinja2Templates(directory="templates")

chat_responses = []

@app.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("home.html", {"request": request, "chat_responses": chat_responses})


chat_log = [{'role': 'system',
             'content': 'You tell jokes.'
             }]


@app.websocket("/ws")
async def chat(websocket: WebSocket):

    await websocket.accept()

    while True:
        user_input = await websocket.receive_text()
        chat_log.append({'role': 'user', 'content': user_input})
        chat_responses.append(user_input)

        try:
            # response = openai.chat.completions.create(
            #     model='gpt-4',
            #     messages=chat_log,
            #     temperature=0.6,
            #     stream=True
            # )
            respose = 'foo'

            ai_response = ''

            # for chunk in response:
            #     if chunk.choices[0].delta.content is not None:
            #         ai_response += chunk.choices[0].delta.content
            #         await websocket.send_text(chunk.choices[0].delta.content)
            # chat_responses.append(ai_response)
            await  websocket.send_text("This is going to be really cool and encourage talmud torah bezrat Hashem!! "
                                       "But it will take a few months until it's ready. ")

        except Exception as e:
            await websocket.send_text(f'Error: {str(e)}')
            break


@app.post("/", response_class=HTMLResponse)
async def chat(request: Request, user_input: Annotated[str, Form()]):

    chat_log.append({'role': 'user', 'content': user_input})
    chat_responses.append(user_input)

    # response = openai.chat.completions.create(
    #     model='gpt-4',
    #     messages=chat_log,
    #     temperature=0.6
    # )

    # bot_response = response.choices[0].message.content
    bot_response = 'foo'
    chat_log.append({'role': 'assistant', 'content': bot_response})
    chat_responses.append(bot_response)

    return templates.TemplateResponse("home.html", {"request": request, "chat_responses": chat_responses})


















