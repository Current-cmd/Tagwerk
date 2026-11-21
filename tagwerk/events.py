"""Websocket broadcast of graph_event messages to the live graph and dashboard pages."""
import asyncio

from fastapi import WebSocket

from tagwerk.contracts import validate


class Broker:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self.history: list[dict] = []  # replayed to late joiners

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.add(ws)
        for event in self.history:
            await ws.send_json(event)

    def disconnect(self, ws: WebSocket) -> None:
        self._clients.discard(ws)

    async def publish(self, event: dict) -> None:
        validate("graph_event", event)
        self.history.append(event)
        if len(self.history) > 400:  # late joiners get the recent past, not the whole day
            del self.history[:-400]
        dead = []
        for ws in list(self._clients):
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)
        await asyncio.sleep(0)


broker = Broker()
