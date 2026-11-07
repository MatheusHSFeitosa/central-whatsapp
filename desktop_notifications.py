"""Keep the notification bus connection alive to receive desktop actions."""
import asyncio
from html import escape
from threading import Thread

from dbus_next import BusType, Variant
from dbus_next.aio import MessageBus
from PySide6.QtCore import QObject, Signal


class DesktopNotifications(QObject):
    delivered = Signal(int, bool)
    clicked = Signal(int)
    dismissed = Signal(int)

    def __init__(self, parent):
        super().__init__(parent)
        self.loop = None
        self.interface = None
        self.tokens = {}

    def send(self, token, icon, summary, body, image, desktop_entry):
        if self.loop is None:
            self.loop = asyncio.new_event_loop()
            self.connection = None
            self.connect_lock = asyncio.Lock()
            Thread(target=self.loop.run_forever, daemon=True).start()
        asyncio.run_coroutine_threadsafe(
            self._send(token, icon, summary, body, image, desktop_entry), self.loop
        )

    async def _send(self, token, icon, summary, body, image, desktop_entry):
        try:
            async with self.connect_lock:
                if self.interface is None:
                    if self.connection is None:
                        self.connection = await MessageBus(bus_type=BusType.SESSION).connect()
                    name = 'org.freedesktop.Notifications'
                    path = '/org/freedesktop/Notifications'
                    node = await self.connection.introspect(name, path)
                    interface = self.connection.get_proxy_object(name, path, node).get_interface(name)
                    capabilities = await interface.call_get_capabilities()
                    if 'actions' not in capabilities:
                        raise RuntimeError('Desktop notification actions unavailable')
                    interface.on_action_invoked(self._action)
                    interface.on_notification_closed(self._closed)
                    self.body_markup = 'body-markup' in capabilities
                    self.interface = interface
            hints = {'desktop-entry': Variant('s', desktop_entry), 'image-path': Variant('s', image)}
            notification_id = await self.interface.call_notify(
                'Central Chats', 0, icon, summary, escape(body) if self.body_markup else body,
                ['default', 'Abrir conversa'], hints, -1
            )
            self.tokens[notification_id] = token
        except Exception:
            self.delivered.emit(token, False)
        else:
            self.delivered.emit(token, True)

    def _action(self, notification_id, action):
        token = self.tokens.get(notification_id)
        if action == 'default' and token is not None:
            self.clicked.emit(token)

    def _closed(self, notification_id, reason):
        token = self.tokens.pop(notification_id, None)
        if token is not None:
            self.dismissed.emit(token)

    def close_notification(self, token):
        if self.loop is not None:
            asyncio.run_coroutine_threadsafe(self._close(token), self.loop)

    async def _close(self, token):
        for notification_id, current in self.tokens.items():
            if current == token:
                break
        else:
            return
        self.tokens.pop(notification_id)
        try:
            await self.interface.call_close_notification(notification_id)
        except Exception:
            pass
