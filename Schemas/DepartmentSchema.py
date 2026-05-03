from pydantic import BaseModel


# ✅ CREATE schema (INPUT)
class DepartmentCreate(BaseModel):
    Dep_name: str
    Dep_head: str
    Dep_icon: str
    bg_color: str
    icon_color: str


# ✅ RESPONSE schema (OUTPUT)
class DepartmentResponse(DepartmentCreate):
    Dep_id: str

    class Config:
        from_attributes = True   