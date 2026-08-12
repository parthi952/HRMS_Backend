from pydantic import BaseModel, ConfigDict
from typing import List, Optional


# ─── Marks Sheet ──────────────────────────────────────────────────────────────

class MarksSheetBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    doc_type: str
    doc_id: str
    link: str
    status: str


class MarksSheetCreate(MarksSheetBase):
    pass


class MarksSheetResponse(MarksSheetBase):
    id: int


# ─── Asset ────────────────────────────────────────────────────────────────────

class AssetBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ass_id: str
    Type: str
    Ass_name: str
    status: str
    Conditon: str
    handover_date: str


class AssetCreate(AssetBase):
    pass


class AssetResponse(AssetBase):
    id: int


# ─── Access ───────────────────────────────────────────────────────────────────

class AccessBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    AccsesName: str


class AccessCreate(AccessBase):
    pass


class AccessResponse(AccessBase):
    id: int


# ─── Requirement ──────────────────────────────────────────────────────────────

class RequirementBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Temp_Id: str
    name: str
    email: str
    department: str
    position: str
    Resume: str


class RequirementCreate(RequirementBase):
    marks_sheets: List[MarksSheetCreate] = []
    assets: List[AssetCreate] = []
    access: List[AccessCreate] = []


class RequirementUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Temp_Id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    Resume: Optional[str] = None


class RequirementResponse(RequirementBase):
    id: int
    marks_sheets: List[MarksSheetResponse] = []
    assets: List[AssetResponse] = []
    access: List[AccessResponse] = []