import json
from typing import Dict, List
from bson import ObjectId
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from fastapi import APIRouter
from users.models.usermodel import EmailCheckRequest, EmailCheckResponse, OTPTable, UserCreate, UserDecision, UserInteraction, UserTable
from users.routes.userAuth import authenticate_user, create_access_token, get_current_user, get_user
import qrcode
from fastapi.responses import StreamingResponse
from io import BytesIO
import random

SECRET_KEY = "9b7f4a8c2dfe5a1234567890abcdef1234567890abcdef1234567890abcddf"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 400000

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

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
        firstPrompt=user.firstPrompt,
        secondPrompt=user.secondPrompt,
        thirdPrompt=user.thirdPrompt,
        interests=user.interests,
        qualities=user.qualities
    )

    new_user.save()
    access_token = create_access_token(data={"sub": user.uuid})
    return {"message": "User created successfully", "access_token": access_token}

@router.get("/users/me")
async def read_users_me(current_user: UserTable = Depends(get_current_user)):
    return {
        "message": "User data",
        "data": {
            "_id": str(current_user.id),  # Convert ObjectId to string
            "uuid": current_user.uuid,
            "email_address": current_user.email_address,
            "fullName": current_user.fullName,
            "profilePicture": current_user.profilePicture,
            "age": current_user.age,
            "gender": current_user.gender,
            "sexual_orientation": current_user.sexual_orientation,
            "location_city": current_user.location_city,
            "location_state": current_user.location_state,
            "interests": current_user.interests,
            "qualities": current_user.qualities,
            "firstPrompt": current_user.firstPrompt,
            "secondPrompt": current_user.secondPrompt,
            "thirdPrompt": current_user.thirdPrompt
        },
        "status": 200
    }


@router.get("/user-find/user/{id}")
async def find_user(id: str, user: UserTable = Depends(get_current_user)):
    find_data = UserTable.objects.get(id=ObjectId(id))
    return {
        "message": "User found successfully",
        "data": {**find_data.to_mongo(), "_id": str(find_data.id)},  # Convert ObjectId to string
        "status": 200
    }


@router.get("/user/match-users/")
async def match_users(user: UserTable = Depends(get_current_user)):
    current_user_doc = UserTable.objects(uuid=user.uuid).first()
    if not current_user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    matching_users = find_matching_users(current_user_doc)
    return {
        "data":matching_users,
        "status": 200
    }


@router.get("/user/accepted-users/")
async def get_accepted_users(user: UserTable = Depends(get_current_user)):
    # Fetch all interactions where the current user has accepted another user
    accepted_interactions = UserInteraction.objects(user_id=user, decision="accept")
    
    # Extract the UUIDs of accepted users
    accepted_user_uuids = [interaction.target_user_id.uuid for interaction in accepted_interactions]

    # Fetch user details of accepted users
    accepted_users = UserTable.objects(uuid__in=accepted_user_uuids)

    return {
        "message": "Accepted users list",
        "data": [{**user.to_mongo(), "_id": str(user.id)} for user in accepted_users],
        "status": 200
    } if accepted_users else {
        "message": "No accepted users found",
        "data": None,
        "status": 404
    }
@router.get("/user/who-accepted-me/")
async def get_users_who_accepted_me(
    current_user: UserTable = Depends(get_current_user)
):
    # 1️⃣ Fetch interactions where OTHER users accepted ME
    accepted_interactions = UserInteraction.objects(
        target_user_id=current_user,
        decision="accept"
    )

    if not accepted_interactions:
        return {
            "message": "No users have to match you yet",
            "data": [],
            "status": 200
        }

    # 2️⃣ Extract user IDs of users who accepted me
    accepted_by_user_uuids = [
        interaction.user_id.uuid
        for interaction in accepted_interactions
    ]

    # 3️⃣ Fetch user details
    accepted_users = UserTable.objects(
        uuid__in=accepted_by_user_uuids
    )

    return {
        "message": "Users who accepted you",
        "data": [
            {**user.to_mongo(), "_id": str(user.id)}
            for user in accepted_users
        ],
        "status": 200
    }
@router.post("/user/make-decision/")
async def make_decision(
    decision: UserDecision,
    current_user: UserTable = Depends(get_current_user)
):
    # current_user is already UserTable
    target_user = UserTable.objects(
        uuid=decision.target_user_id
    ).first()

    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    UserInteraction(
        user_id=current_user,
        target_user_id=target_user,
        decision=decision.decision
    ).save()

    return {
        "message": f"Decision '{decision.decision}' saved",
        "target_user": target_user.fullName,
        "status": 200
    }



@router.get("/user/generate-qr/")
async def generate_qr(user: UserTable = Depends(get_current_user)):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(str(user.id))  # Convert ObjectId to string
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return StreamingResponse(buffer, media_type="image/png")


@router.get("/user/find-by-qr-code/{id}")
async def find_by_qr_code(id: str, user: UserTable = Depends(get_current_user)):
    find_user_data = UserTable.objects.get(id=ObjectId(id))
    if find_user_data:
        return {
            "message": "User found",
            "data": {**find_user_data.to_mongo(), "_id": str(find_user_data.id)},
            "status": 200
        }
    return {
        "message": "User not found",
        "data": None,
        "status": 404
    }


@router.get("/user/all-user-list")
async def all_user_list(current_user: UserTable = Depends(get_current_user)):
    find_data = UserTable.objects.all()
    return {
        "message": "User list",
        "data": [{**user.to_mongo(), "_id": str(user.id)} for user in find_data],
        "status": 200
    } if find_data else {
        "message": "No users registered yet",
        "data": None,
        "status": 404
    }


# Utility Functions
def calculate_age(dob_str):
    dob = datetime.strptime(dob_str, "%d/%m/%Y")
    today = datetime.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return age



import random

def find_matching_users(current_user: UserTable) -> List[Dict]:
    potential_matches = UserTable.objects.exclude('password_hash')

    # Fetch all interactions where the current user has made a decision
    user_interactions = UserInteraction.objects(user_id=current_user, decision__in=["accept", "reject"])
    
    # Store UUIDs of users who were accepted or rejected
    interacted_users = {interaction.target_user_id.uuid for interaction in user_interactions}

    # Filter users: 
    # 1. Exclude current user 
    # 2. Exclude users who were already accepted/rejected
    # 3. Exclude users whose UUID or email is stored as a plain string ("string")
    filtered_users = [
        user for user in potential_matches 
        if user.uuid != current_user.uuid 
        and user.uuid not in interacted_users
        and user.uuid.lower() != "string"  # Exclude if UUID is "string"
        and user.email_address.lower() != "string"  # Exclude if email is "string"
    ]

    # Shuffle to fetch random users
    random.shuffle(filtered_users)

    # Convert to required format
    matching_users = [{
        **user.to_mongo(),
        "_id": str(user.id),
    } for user in filtered_users]

    return matching_users




import random

def generate_otp():
    return str(random.randint(100000, 999999))

from datetime import datetime, timedelta
from fastapi import HTTPException
from pydantic import BaseModel
class EmailCheckRequest(BaseModel):
    email: str
@router.post("/auth/send-otp")
async def send_otp(mobile: EmailCheckRequest):
    print(f"Sending OTP to mobile: {mobile.email}")
    user = UserTable.objects(email_address=f"{mobile.email}").first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    otp = STATIC_OTP
    expiry = datetime.utcnow() + timedelta(minutes=5)

    # Remove old OTPs
    OTPTable.objects(mobile=mobile.email).delete()

    OTPTable(
        mobile=mobile.email,
        otp=otp,
        expires_at=expiry
    ).save()

    # 👉 SMS integration yaha karo (Twilio / Fast2SMS)
    print("OTP:", otp)  # DEV ONLY

    return {
        "message": "OTP sent successfully",
        "expires_in": "5 minutes"
    }

class LoginWithOTPRequest(BaseModel):
    mobile: str
    otp: str

@router.post("/auth/login-with-otp")
async def login_with_otp(data: LoginWithOTPRequest):
    otp_record = OTPTable.objects(
        mobile=data.mobile,
        otp=data.otp,
        expires_at__gte=datetime.utcnow()
    ).first()

    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    user = UserTable.objects(email_address=data.mobile).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    access_token = create_access_token(data={"sub": user.uuid})

    # OTP delete after use
    otp_record.delete()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "uuid": user.uuid,
            "fullName": user.fullName,
            "mobile": data.mobile
        }
    }

@router.post("/check-email", response_model=EmailCheckResponse)
def check_email(data: EmailCheckRequest):
    user = UserTable.objects(email_address=data.email).first()

    if user:
        return {"exists": False}   # ❌ Email already exists
    else:
        return {"exists": True}    # ✅ Email available
    
STATIC_OTP = "1234"           # 🔥 testing ke liye
OTP_EXPIRY_MINUTES = 5  

from pydantic import BaseModel

class SendOTPRequest(BaseModel):
    mobile: str

class VerifyOTPRequest(BaseModel):
    mobile: str
    otp: str
@router.post("/signup/send")
def send_otp(data: SendOTPRequest):
    """
    OTP Send API (static OTP)
    """

    # Purana OTP delete karo
    OTPTable.objects(mobile=data.mobile).delete()

    expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)

    # Naya OTP save
    OTPTable(
        mobile=data.mobile,
        otp=STATIC_OTP,
        expires_at=expires_at
    ).save()

    return {
        "success": True,
        "message": "OTP sent successfully",
        "expires_at": expires_at,
        "otp": STATIC_OTP  # ⚠️ REMOVE in production
    }
@router.post("/signup/verify")
def verify_otp(data: VerifyOTPRequest):
    """
    OTP Verify API
    """

    otp_entry = OTPTable.objects(
        mobile=data.mobile,
        otp=data.otp
    ).first()

    if not otp_entry:
        return {
            "success": False,
            "message": "Invalid OTP"
        }

    # ⏰ Expiry check
    if otp_entry.expires_at < datetime.utcnow():
        otp_entry.delete()
        return {
            "success": False,
            "message": "OTP expired"
        }

    # ✅ Success → OTP delete kar do (one time use)
    otp_entry.delete()

    return {
        "success": True,
        "message": "OTP verified successfully"
    }

# all user list for admin
@router.get("/admin/all-users")
async def get_all_users():
    users = UserTable.objects()

    user_list = []
    for user in users:
        user_list.append({
            "uuid": user.uuid,
            "email_address": user.email_address,
            "fullName": user.fullName,
            "profilePicture": user.profilePicture,
            "age": user.age,
            "gender": user.gender,
            "sexual_orientation": user.sexual_orientation,
            "location_city": user.location_city,
            "location_state": user.location_state,
            "interests": user.interests,
            "qualities": user.qualities,
            "created_at": str(user.id.generation_time)  # optional
        })

    return {
        "success": True,
        "total": len(user_list),
        "users": user_list
    }
