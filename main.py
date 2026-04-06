 # <--- Add this import
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from psycopg2 import Date
from sqlalchemy.orm import Session
from routers import employee
from routers import Attendance as att
from routers import Leave
from contextlib import asynccontextmanager

# Importing your local modules
import models
from database import engine, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # This automatically creates the tables in PostgreSQL/MySQL on startup
    models.Base.metadata.create_all(bind=engine)
    yield
    print("Shutting down...")

app = FastAPI(lifespan=lifespan)

# CORS setup so your frontend can talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router for Api

@app.get("/")
def read_root():
    return {"message": "Employee API is active"}
# emmployee router
app.include_router(employee.router)

# attendance router
app.include_router(att.router)

app.include_router(Leave.router)