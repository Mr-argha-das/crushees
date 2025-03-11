from fastapi import APIRouter, WebSocket, WebSocketDisconnect, FastAPI
from geopy.distance import geodesic
from bson import ObjectId

from nearbyUser.model.nearbyUserModel import ActiveUser
from users.models.usermodel import UserTable

router = APIRouter()
connections = {}

# 📄 WebSocket Documentation
websocket_description = {
    "name": "WebSocket: User Location",
    "description": """
        **Real-time WebSocket for Location Tracking**  
        
        **How to Use:**  
        1️⃣ **Connect:** `ws://yourserver.com/user/location/{user_id}`  
        2️⃣ **Send JSON:** `{"latitude": 12.34, "longitude": 56.78}`  
        3️⃣ **Receive Nearby Users:** `{"nearby_users": [{...}]}`  
        4️⃣ **Auto Update:** When a new user enters your 50m radius  
        
        **Events:**  
        - `"nearby_users"`: List of users near you  
        - `"new_user"`: Notification when a new user enters your area  
    """,
}

async def location_websocket(websocket: WebSocket, user_id: str):
    """Handles WebSocket connections for real-time location updates."""
    await websocket.accept()
    connections[user_id] = websocket

    try:
        while True:
            data = await websocket.receive_json()
            latitude = data.get("latitude")
            longitude = data.get("longitude")

            if latitude is None or longitude is None:
                await websocket.send_json({"error": "Latitude and Longitude required"})
                continue

            ActiveUser.objects(user_id=ObjectId(user_id)).update_one(
                upsert=True,
                set__latitude=latitude,
                set__longitude=longitude
            )

            my_location = (latitude, longitude)
            nearby_users = []

            for user in ActiveUser.objects():
                if str(user.user_id) == user_id:
                    continue  

                user_location = (user.latitude, user.longitude)
                distance = geodesic(my_location, user_location).meters

                if distance <= 50:
                    userData = UserTable.objects.get(id=ObjectId(user.user_id))
                    nearby_users.append({
                        "user_id": str(user.user_id),
                        "user": {
                            "name": userData.fullName,
                            "profilePick": userData.profilePicture
                        },
                        "latitude": user.latitude,
                        "longitude": user.longitude,
                        "distance": round(distance, 2)
                    })

            await websocket.send_json({"nearby_users": nearby_users})
            await broadcast_update(user_id, latitude, longitude)

    except WebSocketDisconnect:
        ActiveUser.objects(user_id=ObjectId(user_id)).delete()
        del connections[user_id]

async def broadcast_update(new_user_id, new_lat, new_lng):
    """Notify all users within 50 meters when a new user joins their area."""
    new_user_location = (new_lat, new_lng)

    for user_id, ws in connections.items():
        if user_id == new_user_id:
            continue

        user = ActiveUser.objects(user_id=ObjectId(user_id)).first()
        if not user:
            continue

        existing_user_location = (user.latitude, user.longitude)
        distance = geodesic(new_user_location, existing_user_location).meters

        if distance <= 50:
            userData = UserTable.objects.get(id=ObjectId(new_user_id))
            await ws.send_json({
                "new_user": {
                    "user_id": str(new_user_id),
                    "user": {
                        "name": userData.fullName,
                        "profilePick": userData.profilePicture
                    },
                    "latitude": new_lat,
                    "longitude": new_lng,
                    "distance": round(distance, 2)
                }
            })

# 📄 Manually add WebSocket API to Swagger UI
def add_api_websocket_route(app: FastAPI):
    """Manually adds WebSocket description to Swagger docs"""
    app.openapi()["paths"]["/user/location/{user_id}"] = {
        "get": {
            "summary": websocket_description["name"],
            "description": websocket_description["description"],
            "responses": {101: {"description": "Switching Protocols"}},
        }
    }

# 🚀 Register WebSocket route in FastAPI
