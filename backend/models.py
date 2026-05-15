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
