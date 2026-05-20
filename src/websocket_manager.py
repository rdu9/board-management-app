from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # key: user_uid string
        # value: their open WebSocket connection
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, user_uid: str, websocket: WebSocket):
        # accept() completes the WebSocket handshake
        # without this the connection never opens
        await websocket.accept()
        # store the connection so we can find it later
        self.active_connections[user_uid] = websocket

    def disconnect(self, user_uid: str):
        # remove from dict when user closes the app or loses connection
        self.active_connections.pop(user_uid, None)

    async def send_notification_websocket(self, user_uid: str, message: dict):
        # find the user's connection if they're online
        websocket = self.active_connections.get(user_uid)
        if websocket:
            # push the message through their open connection
            await websocket.send_json(message)
        # if user is offline, nothing happens
        # they'll get the notification from the DB when they come back online

# single instance shared across the entire app
manager = ConnectionManager()