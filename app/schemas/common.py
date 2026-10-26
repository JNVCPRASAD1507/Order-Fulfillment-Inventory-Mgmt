from pydantic import BaseModel, ConfigDict
from typing import Any
class ORM(BaseModel): model_config=ConfigDict(from_attributes=True)
class ErrorBody(BaseModel): code:str; message:str
class ErrorResponse(BaseModel): success:bool=False; error:ErrorBody
class Message(BaseModel): message:str
