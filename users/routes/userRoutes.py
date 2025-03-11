import json
from typing import Dict, List
from bson import ObjectId
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from fastapi import APIRouter
from users.models.usermodel import UserCreate, UserDecision, UserInteraction, UserTable
from users.routes.userAuth import authenticate_user, create_access_token, get_current_user, get_user
import qrcode
from fastapi.responses import StreamingResponse
from io import BytesIO

SECRET_KEY = "9b7f4a8c2dfe5a1234567890abcdef1234567890abcdef1234567890abcddf"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 400000

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")



# Route to login and get JWT token
@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect UUID or password")

    access_token = create_access_token(data={"sub": user.uuid})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/user/login")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect UUID or password")

    access_token = create_access_token(data={"sub": user.uuid})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/users/create")
async def create_user(user: UserCreate):
    if get_user(user.uuid):
        raise HTTPException(status_code=400, detail="UUID already exists")
    
    hashed_password = pwd_context.hash(user.password)
    new_user = UserTable(
        uuid=user.uuid,
        email_address=user.email_address,
        fullName=user.fullName,
        profilePicture=user.profilePicture,
        age=user.age,
        gender=user.gender,
        password_hash=hashed_password,
        sexual_orientation=user.sexual_orientation,
        location_city=user.location_city,
        location_state=user.location_state,
    )
    
    new_user.save()
    return {"message": "User created successfully"}

# Protected route to get user details
@router.get("/users/me")
async def read_users_me(current_user: UserTable = Depends(get_current_user)):
    return {
        "message": "User data",
        "data": {
            "_id": str(ObjectId(current_user.id)),
            "uuid": current_user.uuid,
        "email_address": current_user.email_address,
        "fullName": current_user.fullName,
        "profilePicture": current_user.profilePicture,
        "age": current_user.age,
        "gender": current_user.gender,
        "sexual_orientation": current_user.sexual_orientation,
        "location_city": current_user.location_city,
        "location_state": current_user.location_state,
        },
        "status": 200
    }

@router.get("/user-find/user/{id}")
async def findUser(id: str , user: UserTable = Depends(get_current_user)):
    finadata = UserTable.objects.get(id=ObjectId(id))
    return {
        "message": "User find success",
        "data": json.loads(finadata.to_json()),
        "status": 2000
    }


def calculate_compatibility_score(current_user: UserTable, other_user: UserTable) -> float:
    # Define weights for each factor
    WEIGHTS = {
        "age": 0.2,
        "location": 0.3,
        "interests": 0.25,
        "qualities": 0.25,
    }

    # Age compatibility (within ±5 years)
    current_age = int(current_user.age)
    other_age = int(other_user.age)
    age_diff = abs(current_age - other_age)
    age_score = max(0, 1 - (age_diff / 10))  # Normalize to [0, 1]

    # Location compatibility (same city = 1, same state = 0.5, else = 0)
    if current_user.location_city == other_user.location_city:
        location_score = 1.0
    elif current_user.location_state == other_user.location_state:
        location_score = 0.5
    else:
        location_score = 0.0

    # Interests compatibility (Jaccard similarity)
    current_interests = set(current_user.interests)
    other_interests = set(other_user.interests)
    common_interests = current_interests.intersection(other_interests)
    interests_score = len(common_interests) / max(len(current_interests), len(other_interests), 1)

    # Qualities compatibility (Jaccard similarity)
    current_qualities = set(current_user.qualities)
    other_qualities = set(other_user.qualities)
    common_qualities = current_qualities.intersection(other_qualities)
    qualities_score = len(common_qualities) / max(len(current_qualities), len(other_qualities), 1)

    # Calculate weighted compatibility score
    compatibility_score = (
        WEIGHTS["age"] * age_score +
        WEIGHTS["location"] * location_score +
        WEIGHTS["interests"] * interests_score +
        WEIGHTS["qualities"] * qualities_score
    )

    return round(compatibility_score, 2)

def find_matching_users(current_user: UserTable) -> List[Dict]:
    # Filter users based on gender and sexual orientation
    if current_user.sexual_orientation == "heterosexual":
        target_gender = "male" if current_user.gender == "female" else "female"
    elif current_user.sexual_orientation == "homosexual":
        target_gender = current_user.gender
    else:  # bisexual or other
        target_gender = None

    # Query the database for potential matches
    query = {}
    if target_gender:
        query["gender"] = target_gender

    # Exclude users that the current user has already denied
    denied_users = UserInteraction.objects(user_id=current_user, decision="deny").values_list('target_user_id')
    query["uuid__nin"] = [user.uuid for user in denied_users]

    potential_matches = UserTable.objects(**query).exclude('password_hash')

    # Calculate compatibility scores for each potential match
    matching_users = []
    for user in potential_matches:
        if user.uuid == current_user.uuid:  # Skip the current user
            continue
        compatibility_score = calculate_compatibility_score(current_user, user)
        matching_users.append({
            **user.to_mongo(),
            "compatibility_score": compatibility_score
        })

    # Sort users by compatibility score (highest first)
    matching_users.sort(key=lambda x: x["compatibility_score"], reverse=True)

    return matching_users

# FastAPI Endpoint to Get Matches
@router.get("/user/match-users/", )
async def match_users(user: UserTable = Depends(get_current_user)):
    # Convert the Pydantic model to a MongoEngine document
    current_user_doc = UserTable.objects(uuid=user.uuid).first()
    if not current_user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    # Find matching users
    matching_users = find_matching_users(current_user_doc)

    # Return the matching users
    return matching_users

# FastAPI Endpoint to Accept or Deny a User
@router.post("/user/make-decision/")
async def make_decision(decision: UserDecision,user: UserTable = Depends(get_current_user)):
    # Find the current user and target user

    current_user = UserTable.objects(uuid=decision.user_id).first()
    target_user = UserTable.objects(uuid=decision.target_user_id).first()

    if not current_user or not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Save the decision in the UserInteraction collection
    UserInteraction(
        user_id=current_user,
        target_user_id=target_user,
        decision=decision.decision
    ).save()

    return {"message": f"Decision '{decision.decision}' saved for user {target_user.fullName}"}

@router.get("/user/generate-qr/")
def generate_qr(user: UserTable = Depends(get_current_user)):
    # Generate the QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    print(ObjectId(user.id))
    qr.add_data(ObjectId(user.id))
    qr.make(fit=True)

    # Create an image from the QR Code instance
    img = qr.make_image(fill_color="red", back_color="white")

    # Save the image to a bytes buffer
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    # Return the image as a response
    return StreamingResponse(buffer, media_type="image/png")


@router.get("/user/find-by-qr-code/{id}")
def findByQrCode(id:str,user: UserTable = Depends(get_current_user) ):
    finduserData = UserTable.objects.get(id=ObjectId(id))
    if finduserData:
        return {
            "message": "user found",
            "data": json.loads(finduserData.to_json()),
            "status": 200
        }
    else :
      return {
            "message": "user not found",
            "data": None,
            "status": 200
    }