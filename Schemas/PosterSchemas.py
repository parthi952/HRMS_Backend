from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional


class PostingSchema_create(BaseModel):
    PostId: str
    title: str
    department: str
    stack: str
    salary: str
    experience: str
    education: str
    methods: str
    perks: str
    Description: str
    applyLink: str

class ATS_PostSchema(BaseModel):
    PostId: str
    Title: str
    Skills: str
    Education: str
    Experience: str
    Abilities: str

class JobPost_SocialMedia_MappingSchema(BaseModel):
    PostId: str
    SocialMedia: str

class education_OptionsSchema(BaseModel):
    Edu_name: str

class AI_ModelSchema(BaseModel):
    Model_Name: str
    Avatar: Optional[str] = "bottts"
    Tone_Id: Optional[str] = None


class AIModeSchema(BaseModel):
    Mode_Type: str
    Prompt: str
    Icon: Optional[str] = "Bot"
    model_id: Optional[str] = None

class SelectionCheckListSchema(BaseModel):
    CheckList_Name: str
    enable: bool
    model_id: Optional[str] = None



class JobDetailsRequest(BaseModel):
    PostId: str
    title: str
    department: str
    stack: str
    salary: str
    experience: str
    education: str
    methods: str
    perks: str
    Description: str
    applyLink: str


class AiGenerationRequestSchema(BaseModel):
    JobDetails: JobDetailsRequest
    AI_Model: List[AI_ModelSchema]
    AIMode: List[AIModeSchema]
    SelectionCheckList: List[SelectionCheckListSchema]

class AiJobPostSchema(BaseModel):
    PostId: str
    Title: str
    Poster: str