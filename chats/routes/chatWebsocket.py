from fastapi import APIRouter, WebSocket, WebSocketDisconnect, FastAPI
from typing import Dict

from chats.model.chatsModel import Conversation, Message

router = APIRouter()

class ConnectionManager:
    """Handles private WebSocket connections."""
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)

    async def send_private_message(self, sender_id: str, receiver_id: str, message: str):
        receiver_socket = self.active_connections.get(receiver_id)
        
        # Store message in MongoDB
        msg = Message(sender_id=sender_id, receiver_id=receiver_id, message=message)
        msg.save()

        # Update or create conversation
        conversation = Conversation.objects(participants__all=[sender_id, receiver_id]).first()
        if not conversation:
            conversation = Conversation(participants=[sender_id, receiver_id], last_message=msg)
        else:
            conversation.last_message = msg
        conversation.save()

        if receiver_socket:
            await receiver_socket.send_json({
                "sender_id": sender_id,
                "message": message
            })

manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """Handles WebSocket connections for private messaging."""
    await manager.connect(websocket, user_id)
    

    try:
        while True:
            data = await websocket.receive_json()
            receiver_id = data.get("receiver_id")
            message = data.get("message")

            if not receiver_id or not message:
                await websocket.send_json({"error": "Missing receiver_id or message"})
                continue

            await manager.send_private_message(user_id, receiver_id, message)

    except WebSocketDisconnect:
        manager.disconnect(user_id)

# 📄 WebSocket API Documentation
websocket_description = {
    "name": "WebSocket: Private Chat",
    "description": """
        **Real-time WebSocket for Private Messaging**  
        
        **How to Use:**  
        1️⃣ **Connect:** `ws://yourserver.com/chat/ws/{user_id}`  
        2️⃣ **Send JSON:** `{"receiver_id": "USER_ID", "message": "Hello"}`  
        3️⃣ **Receive Messages:** `{"sender_id": "USER_ID", "message": "Hi!"}`  
        
        **Events:**  
        - `"message"`: New message from another user  
        - `"disconnect"`: User leaves the chat  
    """,
}

# 📄 Manually add WebSocket API to Swagger UI
def add_api_websocket_route(app: FastAPI):
    """Manually adds WebSocket description to Swagger docs"""
    app.openapi()["paths"]["/chat/ws/{user_id}"] = {
        "get": {
            "summary": websocket_description["name"],
            "description": websocket_description["description"],
            "responses": {101: {"description": "Switching Protocols"}},
        }
    }

# 🚀 Register WebSocket route in FastAPI

