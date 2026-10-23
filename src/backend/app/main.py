import logging

from fastapi import FastAPI

from app.api.v1.router import api_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="IDIM API", version="0.1.0")
app.include_router(api_router)
