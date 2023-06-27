from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Date, DateTime, Integer, SmallInteger, String
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel as PydanticBaseModel
from dateutil import parser as date_parser

Base = declarative_base()


#Class used to interact with C# Code
class Actor(Base):
    __tablename__ = 'actor'

    actor_id = Column(SmallInteger, primary_key=True, index=True)
    first_name = Column(String(length=45))
    last_name = Column(String(length=45))
    last_update = Column(DateTime, nullable=False) 
     
#Class used to interact with API (https://jsonplaceholder.typicode.com  
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    username = Column(String, index=True)
    email = Column(String, index=True)

#Class used to interact with API (https://jsonplaceholder.typicode.com
class Post(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100))
    body = Column(String)

    def __repr__(self):
        return f"<Post(id={self.id}, title='{self.title}', body='{self.body}')>"