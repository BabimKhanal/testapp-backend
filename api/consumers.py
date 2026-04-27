# api/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        print("WS CONNECT user:", self.user)

        if self.user.is_anonymous:
            print("WS anonymous - closing")
            await self.close()
            return

        self.room_group_name = f"user_{self.user.id}"
        print("WS joining group:", self.room_group_name)

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        print("WS accepted for", self.room_group_name)
    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name,
            )

    async def private_message(self, event):
        print("WS private_message event for", self.user.id, event)
        await self.send(text_data=json.dumps({
            "type": "private_message",
            "message": event["message"],
        }))