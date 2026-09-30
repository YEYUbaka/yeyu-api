from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class EmailAddressRequest(SQLModel):
    email: EmailStr


class OpaqueTokenRequest(SQLModel):
    token: str = Field(min_length=1, max_length=512)


class GitHubLinkRequest(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)


class OAuthIdentityPublic(SQLModel):
    provider: str
    email: EmailStr
    email_verified: bool
