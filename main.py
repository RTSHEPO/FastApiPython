import datetime
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy import Date, DateTime, asc, create_engine, Column, SmallInteger, String, desc
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import IntegrityError
import databases
import httpx
import uvicorn
from models import Actor, Base, Post, User
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dateutil import parser
import requests




# Create connection to a database 
SQLALCHEMY_DATABASE_URL = 'sqlite:///database.db'
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

app = FastAPI()

database = databases.Database(SQLALCHEMY_DATABASE_URL)

@app.get('/api/actor/')
async def get_actors():
    query = Actor.__table__.select().order_by(asc(Actor.actor_id))
    return await database.fetch_all(query)

# Implement other CRUD operations using SQLAlchemy
@app.post("/api/actor")
async def create_actor(item: dict):
    session = SessionLocal()
    current_datetime = parser.parse(datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
    item["last_update"] = current_datetime
    actor = Actor(**item)    
    session.add(actor)
    session.commit()
    session.refresh(actor)
    return actor

@app.get("/api/actor/{actor_id}")
async def get_actor_by_id(actor_id: int):
    session = SessionLocal()
    actor = session.query(Actor).filter(Actor.actor_id == actor_id).first()
    if actor is None:
        return {"error": "Actor not found"}
    return actor


@app.put("/api/actor/{actor_id}")
async def update_actor(actor_id: int, item: dict):
    session = SessionLocal()
    actor = session.query(Actor).filter(Actor.actor_id == actor_id).first()
    if actor is None:
        return {"error": "Actor not found"}
    for key, value in item.items():
        if key == 'last_update': 
            item[key] =parser.parse(datetime.datetime.now().date())
        setattr(actor, key, value)
    session.commit()
    session.refresh(actor)
    return actor


@app.delete("/api/actor/{actor_id}")
async def delete_actor(actor_id: int):
    session = SessionLocal()
    actor = session.query(Actor).filter(Actor.actor_id == actor_id).first()
    if actor is None:
        return {"error": "Actor not found"}
    session.delete(actor)
    session.commit()
    return {"message": "Actor deleted"}

# External API interaction and database updates using JSONPlaceholder API https://jsonplaceholder.typicode.com 
@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://jsonplaceholder.typicode.com/users/{user_id}")
        if response.status_code == 200:
            user_data = response.json()
            user = User(
                id=user_data["id"],
                name=user_data["name"],
                username=user_data["username"],
                email=user_data["email"]
            )
            db = SessionLocal()
            db.merge(user)
            db.commit()            
            return user
        else:
            return JSONResponse(content={"message": "User not found"}, status_code=404)

@app.get("/api/process-and-update-data")
def process_and_update_data():  
    response = requests.get('https://jsonplaceholder.typicode.com/posts')
    posts = response.json()

    title_dict = {}

    for post in posts:
        title = post['title']

        if title in title_dict:           
            title_dict[title] += 1
            post['title'] = f"{title} ({title_dict[title]})"
        else:         
            title_dict[title] = 1

    db = SessionLocal()

    for post in posts:
        response = requests.put(f"https://jsonplaceholder.typicode.com/posts/{post['id']}", json=post)
        print(f"Post {post['id']} updated. Status code: {response.status_code}")

      
        db_post = Post(id=post['id'], title=post['title'], body=post['body'])
        db.add(db_post)

    db.commit()
    db.close()


@app.get('/api/posts/')
async def get_actors():
    query = Post.__table__.select()
    return await database.fetch_all(query)


class Message(BaseModel):  

    actor_id = Column(SmallInteger,)
    first_name = Column(String)
    last_name = Column(String)
    last_update=Column(DateTime)

    class Config:
        arbitrary_types_allowed = True




async def save_data_to_database(json_data):
    table_name = "actor"  

    if isinstance(json_data, list):
        for record in json_data:
            await save_single_record(record, table_name)
    else:
        await save_single_record(json_data, table_name)

async def save_single_record(json_data, table_name):
    record_id = json_data.get('actor_id')
    record_fname = json_data.get('first_name')
    record_lname = json_data.get('last_name')
    record_date = parser.parse(json_data.get('last_update')) 

    if record_id and record_fname and record_lname and record_date:
        query = f"""
            INSERT INTO {table_name} (actor_id, first_name, last_name, last_update)
            VALUES (:actor_id, :first_name, :last_name, :last_update)
            ON CONFLICT (actor_id) DO UPDATE SET first_name = :first_name, last_name = :last_name, last_update = :last_update
        """
        values = {
            'actor_id': record_id,
            'first_name': record_fname,
            'last_name': record_lname,
            'last_update': record_date
        }

        session = SessionLocal()

        try:            
            session.execute(query, values)           
            session.commit()

            print(f"Record inserted: actor_id={record_id}, first_name={record_fname}, last_name={record_lname}, last_update={record_date}")
        except Exception as e:
            print(f"Failed to insert record: {e}")
            session.rollback()        
    else:
        print("Invalid JSON data. Missing required fields.")
 
# Implement other API endpoints as needed

# WebSocket API
@app.websocket("/ws/advanced")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()    
    while True:
        data = await websocket.receive_text()        
        if data == "ping":
            await websocket.send_text("pong")
        elif data == "echo":
            await websocket.send_text("echo: " + data)
        else:
            try:
                json_data = json.loads(data)
                await save_data_to_database(json_data)
                await websocket.send_text("Data processed and database updated.")
            except json.JSONDecodeError:
                await websocket.send_text("Invalid JSON data.")             
 
@app.websocket("/ws/ping")
async def websocket_ping(websocket: WebSocket):
    await websocket.accept()
    while True:
        actor = await websocket.receive_text()
        await websocket.send_text(f"Pong: {actor}")


@app.websocket("/ws/echo")
async def websocket_echo(websocket: WebSocket):
    await websocket.accept()
    while True:
        actor = await websocket.receive_text()
        await websocket.send_text(f"You said: {actor}")

if __name__ == '__main__':    
    uvicorn.run(app, host='0.0.0.0', port=8000, ws_ping_interval=10, ws_timeout=120)  
