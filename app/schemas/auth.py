from pydantic import BaseModel, EmailStr, Field
from app.models.entities import Role
from app.schemas.common import ORM
class RegisterIn(BaseModel): email:EmailStr; full_name:str=Field(min_length=2,max_length=120); password:str=Field(min_length=8); role:Role=Role.CUSTOMER
class LoginIn(BaseModel): email:EmailStr; password:str
class RefreshIn(BaseModel): refresh_token:str
class TokenOut(BaseModel): access_token:str; refresh_token:str; token_type:str="bearer"
class UserOut(ORM): id:int; email:EmailStr; full_name:str; role:Role; is_active:bool
class ChangePasswordIn(BaseModel): current_password:str; new_password:str=Field(min_length=8)
