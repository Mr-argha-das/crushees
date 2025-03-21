from mongoengine import connect
from fastapi import FastAPI
from users.routes import userRoutes, uploadRoutes
from things.routes import thingsRoutes
from qualities.routes import qualitiesRoutes
from chats.routes import chatsRoutes, chatWebsocket
from nearbyUser.routes import nearbyUserRoutes

app = FastAPI()
connect('11554566', host="mongodb+srv://avbigbuddy:nZ4ATPTwJjzYnm20@cluster0.wplpkxz.mongodb.net/11554566")

app.include_router(userRoutes.router, tags=["Users"])
app.include_router(uploadRoutes.router, tags=["Users"])
app.include_router(thingsRoutes.router, tags=["Things"])
app.include_router(qualitiesRoutes.router, tags=["qualities"])
app.include_router(chatsRoutes.router, tags=["Chats"])
app.include_router(chatWebsocket.router, tags=["Chats"])
app.add_api_websocket_route("/user/location/{user_id}", nearbyUserRoutes.location_websocket)
nearbyUserRoutes.add_api_websocket_route(app)
app.add_api_websocket_route("/chat/ws/{user_id}", chatWebsocket.websocket_endpoint)
chatWebsocket.add_api_websocket_route(app)



import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", port=8080, reload=True)