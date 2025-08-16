from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from controllers.chat import chat_router
from controllers.users import user_router
from fastapi.middleware.cors import CORSMiddleware

allowed_origins = [
    "http://localhost:3000",
]



app = FastAPI()
app.include_router(chat_router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(user_router, prefix="/api/v1/users", tags=["users"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)