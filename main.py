# <--- Add this import
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from psycopg2 import Date
from sqlalchemy.orm import Session
from routers import (CustomID, Department,
    PayRoll,
    employee,
    Candidate,
    JobPost,
    ATS_Score,
    Dashboard,
    OffBoard,
    Compat,
)
from Caluclation import Currency
from routers import Attendance as att
from routers import Leave
from routers import option, Requirement
from contextlib import asynccontextmanager
from Auth import router as Auth
from EmployeePort.Atteddance.Attendance import router as employee_attendance_router
from EmployeePort.ActiveBatch import router as active_batch_router
from routers.PdfRouter import router as pdf_router
from DailyTaskReport.Routere import router as daily_tasks_router
from UserPassword import PortAccsesRoute as PortAccses
from Auth.sso_router import router as sso_router
# pyrefly: ignore [missing-import]
from ManagerPort.M_Leave import router as ManagerPort_Leave
from Festival.FestivalRouter import router as festival_router, seed_default_festivals, seed_default_template, run_daily_festival_check
from apscheduler.schedulers.background import BackgroundScheduler



# Importing your local modules
import module.EmplyeeDB as EmplyeeDB
import module.PayrollDB as PayrollDB
import DailyTaskReport.moduale as DailyTaskReportDB
import module.CandidateDB as CandidateDB
import module.RequirementDB as RequirementDB
import module.ATSScoreDB as ATSScoreDB
import module.FestivalDB as FestivalDB
from database import engine, get_db


import module.OffBoardDB as OffBoardDB

scheduler = BackgroundScheduler()


def _festival_job():
    import asyncio
    asyncio.run(run_daily_festival_check())


@asynccontextmanager
async def lifespan(app: FastAPI):

    EmplyeeDB.Base.metadata.create_all(bind=engine)
    ATSScoreDB.Base.metadata.create_all(bind=engine)
    OffBoardDB.Base.metadata.create_all(bind=engine)
    FestivalDB.Base.metadata.create_all(bind=engine)
    seed_default_festivals()
    seed_default_template()

    scheduler.add_job(_festival_job, "cron", hour=8, minute=30, id="festival_check", replace_existing=True)
    scheduler.start()

    yield
    scheduler.shutdown(wait=False)
    print("Shutting down...")


app = FastAPI(lifespan=lifespan,root_path="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# Router for Api


@app.get("/")
def read_root():
    return {"message": "Employee API is active"}



app.include_router(Auth.router)


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

app.include_router(Currency.router,prefix="/currency")
app.include_router(daily_tasks_router)

app.include_router(sso_router)
app.include_router(PortAccses.router, prefix="/PortAccses")
app.include_router(PortAccses.router, prefix="/Auth")
app.include_router(ManagerPort_Leave)

# New routers to fill frontend gaps
app.include_router(Dashboard.router)
app.include_router(OffBoard.router)
app.include_router(Compat.router)
app.include_router(festival_router)
