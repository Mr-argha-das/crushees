import json
from bson import ObjectId
from fastapi import Depends, HTTPException, APIRouter

from chats.model.chatsModel import Conversation, Message
from users.models.usermodel import UserTable
from users.routes.userAuth import get_current_user
from .chatWebsocket import manager

router = APIRouter()
def is_valid_object_id(value):
    try:
        ObjectId(str(value))
        return True
    except Exception:
        return False

# =========================
# GET INBOX
@router.get("/chats/inbox")
async def get_inbox(current_user: UserTable = Depends(get_current_user)):
    current_user_id = str(ObjectId(current_user.id))

    conversations = Conversation.objects(
        participants=current_user_id
    ).order_by("-last_message__timestamp")

    inbox_list = []

    for convo in conversations:
        # ✅ safely extract other user id
        other_user_id = None

        for p in convo.participants:
            if p != current_user_id and is_valid_object_id(p):
                other_user_id = p
                break

        # ❌ if no valid other user → skip this conversation
        if not other_user_id:
            continue

        try:
            user = UserTable.objects.get(id=ObjectId(other_user_id))
        except Exception:
            # user deleted / invalid reference
            continue

        # last message text logic
        if convo.last_message.sender_id == current_user_id:
            last_message_text = (
                "seen just now"
                if convo.last_message.is_read
                else "Sent just now"
            )
        else:
            last_message_text = convo.last_message.message

        inbox_list.append({
            "conversation_id": str(convo.id),
            "other_user": {
                "_id": str(ObjectId(user.id)),
                "name": user.fullName,
                "profilePick": user.profilePicture
            },
            "last_message": last_message_text,
            "timestamp": convo.last_message.timestamp
        })

    return {
        "message": "Here is all Conversation",
        "inbox": inbox_list,
        "status": 200
    }

# =========================
# CHAT HISTORY
# =========================
@router.get("/chats/history/{user2}")
async def get_chat_history(
    user2: str,
    current_user: UserTable = Depends(get_current_user)
):
    current_user_id = str(ObjectId(current_user.id))

    messages = Message.objects(
        sender_id__in=[current_user_id, user2],
        receiver_id__in=[current_user_id, user2]
    ).order_by("timestamp")

    return {
        "message": "All chats",
        "chat": [
            {
                "sender_id": msg.sender_id,
                "receiver_id": msg.receiver_id,
                "message": msg.message,
                "timestamp": msg.timestamp,
                "is_me": msg.sender_id == current_user_id
            }
            for msg in messages
        ],
        "status": 200
    }


# =========================
# MARK MESSAGES AS READ
# =========================
@router.post("/chats/mark-read/{user2}")
async def mark_messages_read(
    user2: str,
    current_user: UserTable = Depends(get_current_user)
):
    current_user_id = str(ObjectId(current_user.id))

    # 1️⃣ check unread messages
    unread_count = Message.objects(
        sender_id=user2,
        receiver_id=current_user_id,
        is_read=False
    ).count()

    if unread_count == 0:
        return {"status": 200, "message": "No unread messages"}

    # 2️⃣ mark messages read
    Message.objects(
        sender_id=user2,
        receiver_id=current_user_id,
        is_read=False
    ).update(set__is_read=True)

    # 3️⃣ update conversation
    convo = Conversation.objects(
        participants__all=[current_user_id, user2]
    ).first()

    if convo and convo.last_message.sender_id == user2:
        convo.last_message.is_read = True
        convo.last_message.save()
        convo.save()

        # 🔔 notify sender (✓✓)
        await manager.send_seen_event(
            sender_id=user2,
            seen_by=current_user_id
        )

    return {
        "status": 200,
        "message": "Messages marked as read"
    }
