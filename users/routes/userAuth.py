from users.models.usermodel import UserTable
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from mongoengine import connect, Document, StringField, BooleanField


SECRET_KEY = "9b7f4a8c2dfe5a1234567890abcdef1234567890abcdef1234567890abcddf"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 400000


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
# OAuth2 token authentication
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Function to get user by UUID
def get_user(uuid: str):
    return UserTable.objects(uuid=uuid).first()

# Function to authenticate user
def authenticate_user(uuid: str, password: str):
    user = get_user(uuid)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user

# Function to create JWT token
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Dependency to get the current user from token
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        uuid: str = payload.get("sub")
        if uuid is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = get_user(uuid)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")