from pydantic import BaseModel


class JobListing(BaseModel):
    title: str
    url: str | None = None
    description: str | None = None


class CompanyProfile(BaseModel):
    name: str
    website: str | None = None
    careers_url: str | None = None
    description: str | None = None
    funding: str | None = None
    hiring_signals: list[str] = []
    jobs: list[JobListing] = []


class DiscoverRequest(BaseModel):
    prompt: str


class ApplyRequest(BaseModel):
    company: dict
    analysis: dict


class AutoApplyAnalyzeRequest(BaseModel):
    job_url: str
    job_title: str = ""
    company_name: str = ""


class AutoApplyFillRequest(BaseModel):
    session_id: str
    fields: list[dict]


class AutoApplySubmitRequest(BaseModel):
    session_id: str
