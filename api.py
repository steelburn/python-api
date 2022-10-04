from typing import Dict
from unittest import defaultTestLoader
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import mariadb as database
from pydantic import BaseModel, EmailStr
import requests
import json
import base64
from datetime import datetime, timedelta
import redis
import os
from dotenv import load_dotenv

load_dotenv()

class LoginPair(BaseModel):
    email: EmailStr
    password: str
    
class EncodeText(BaseModel):
    plaintext: str

class AdminProfileType(BaseModel):
    value: bool
    level: str
    
class AuthOut(BaseModel):
    expires_in: int
    login_type: str
    admin_profile: AdminProfileType
    access_token: str

try:
    conn = database.connect(
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_DATABASE","cloud_services_db_dev")
    )
    cur = conn.cursor(dictionary=True)
except database.Error as e:
    print(f"Error connecting to Mariadb Platform: {e}")
    
app = FastAPI()

redis_host = os.getenv("REDIS_HOST","127.0.0.1")
redis_port = int(os.getenv("REDIS_PORT","6379"))
redis_username = os.getenv("REDIS_USER","default")
redis_password = os.getenv("REDIS_PASSWORD","redispw")
r = redis.Redis(host=redis_host,port=redis_port, username=redis_username, password=redis_password)

t = datetime.utcnow()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
base_url = os.getenv("API_BASE_URL","https://appcore.beesuite.app/api")

async def get_auth_session(token: str = Depends(oauth2_scheme)):
    if r.exists(token) == 0:
        raise HTTPException(status_code=401, detail="Authorization expired.")
    else:
        r.expire(token,timedelta(minutes=5))
    return token

@app.get('/')
async def root(token: str = Depends(get_auth_session)):
    return {"message": "FastAPI API",
            "token": token} 

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    to_encode = EncodeText(plaintext=form_data.password)
    encoded_password = await encode(to_encode)
    loginpair = LoginPair(email=form_data.username, password=encoded_password)
    userauth = await authenticate(loginpair)
    print(userauth)
    try:
        return {"access_token": userauth["access_token"], "token_type": "bearer"}
    except:
        return userauth

@app.post('/auth', tags=["authentication"], response_model=AuthOut)
async def authenticate(login: LoginPair):
    auth_url = base_url + "/auth/login"
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(auth_url, json={'email': login.email, 'password': login.password}, headers=headers)
        authdata = response.json()
        print(response.elapsed)
        authresp = json.loads(json.dumps(authdata).encode('utf-8').decode('ascii','ignore'))
        response.raise_for_status()
        try:
            r.setex(authresp["access_token"],timedelta(minutes=5), value="True")
        except:
            print("WARNING: Unable to use Redis.")
    except requests.exceptions.HTTPError as err:
        if err.response.status_code == 401:
            raise HTTPException(status_code=err.response.status_code, detail="Not authorized.")
        else:
            raise HTTPException(status_code=err.response.status_code, detail=err)
    return authresp

@app.post('/encode', tags=["authentication"])
async def encode(text: EncodeText):
    encoded = base64.b64encode(text.plaintext.encode('ascii'))
    return encoded.decode()

@app.get('/users/{userId}')
async def user(userId, token: str = Depends(get_auth_session)):
    cur.execute("SELECT USER_GUID, STAFF_ID, LOGIN_ID, EMAIL FROM user_main WHERE LOGIN_ID=? LIMIT 1", (userId,))
    return cur.fetchone()

@app.get('/logout')
async def deauth(token: str = Depends(get_auth_session)):
    r.expire(token,3)
    return {"logout": "Success"}