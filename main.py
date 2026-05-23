# <--- Add this import
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from psycopg2 import Date
from sqlalchemy.orm import Session
from routers import (
    CustomID,
    Department,
    PayRoll,
    employee,
    Candidate,
    JobPost,
    ATS_Score,
)
from routers import Attendance as att
from routers import Leave
from routers import option, Requirement
from contextlib import asynccontextmanager
from Auth import router as Auth
from EmployeePort.Atteddance.Attendance import router as employee_attendance_router
from EmployeePort.ActiveBatch import router as active_batch_router
from routers.PdfRouter import router as pdf_router
from DailyTaskReport.Routere import router as daily_tasks_router


# Importing your local modules
import module.EmplyeeDB as EmplyeeDB
import module.PayrollDB as PayrollDB
import DailyTaskReport.moduale as DailyTaskReportDB
import module.CandidateDB as CandidateDB
import module.RequirementDB as RequirementDB
import module.ATSScoreDB as ATSScoreDB
from database import engine, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # This automatically creates the tables in PostgreSQL/MySQL on startup
    EmplyeeDB.Base.metadata.create_all(bind=engine)
    ATSScoreDB.Base.metadata.create_all(bind=engine)
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
app.include_router(employee_attendance_router)
app.include_router(active_batch_router)
app.include_router(pdf_router)

app.include_router(Leave.router)

app.include_router(PayRoll.router)

app.include_router(option.router)

app.include_router(Department.router)

app.include_router(CustomID.router)

app.include_router(Candidate.router)

app.include_router(Requirement.router)

app.include_router(JobPost.router)

app.include_router(ATS_Score.router)

app.include_router(Auth.router)
app.include_router(daily_tasks_router)
