import json
from bson import ObjectId
from fastapi import Depends, HTTPException, APIRouter

from chats.model.chatsModel import Conversation, Message
from users.models.usermodel import UserTable
from users.routes.userAuth import get_current_user

router = APIRouter()

@router.get("/chats/inbox")
async def get_inbox(current_user: UserTable = Depends(get_current_user)):
    conversations = Conversation.objects(
        participants=str(ObjectId(current_user.id))
    ).order_by("-last_message__timestamp")

    if not conversations:
        raise HTTPException(status_code=404, detail="No conversations found.")

    inbox_list = []
    for convo in conversations:
        other_user_id = [p for p in convo.participants if p != str(ObjectId(current_user.id))][0]
        user = UserTable.objects.get(id=ObjectId(other_user_id))  # Fetch other user details

        # Fix: Ensure the correct last message display
        if convo.last_message.sender_id == str(ObjectId(current_user.id)):
            last_message_text = "seen just now" if convo.last_message.is_read else "Sent just now"
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

    return {"message": "Here is all Conversation", "inbox": inbox_list, "status": 200}


@router.get("/chats/history/{user2}")
async def get_chat_history( user2: str, current_user: UserTable = Depends(get_current_user)):
    messages = Message.objects(
        sender_id__in=[str(ObjectId(current_user.id)), user2],
        receiver_id__in=[str(ObjectId(current_user.id)), user2]
    ).order_by("timestamp")

    return {
        "message":"All chats",
        "chat": [{"sender": msg.sender_id, "message": msg.message, "timestamp": msg.timestamp} for msg in messages], "status": 200}


@router.post("/chats/mark_seen/{conversation_id}")
async def mark_messages_as_seen(conversation_id: str, current_user: UserTable = Depends(get_current_user)):
    conversation = Conversation.objects.get(id=ObjectId(str(conversation_id)))

    if str(ObjectId(current_user.id)) not in conversation.participants:
        raise HTTPException(status_code=403, detail="Not authorized to access this chat.")

    # Update all messages where the current user is the receiver
    Message.objects(
        receiver_id=str(ObjectId(current_user.id)), 
        sender_id__in=conversation.participants,  # Ensure it's from the other user
        is_read=False
    ).update(set__is_read=True)

    # Update conversation last_message if it's from the sender
    if conversation.last_message and conversation.last_message.receiver_id == str(ObjectId(current_user.id)):
        conversation.last_message.is_read = True
        conversation.last_message.save()

    return {"message": "Messages marked as seen", "status": 200}


