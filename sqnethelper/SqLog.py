import sys
import datetime
import websockets
import asyncio
import threading
import enum
import json

class LogLevel(enum.IntEnum):
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    GREAT = 4

class SqLog:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(SqLog, cls).__new__(cls)
                    cls._instance.__init__()
        return cls._instance

    def __init__(self):
        self.output_methods = set()
        self.log_level = LogLevel.INFO
        self.file = None
        self.websocket_url = None
        self.lock = threading.Lock()
        self.user_connections = {}
        self.default_connections = {}
        self.channels = ['default']
        self.message_queue = asyncio.Queue()

    def set_file_output(self, filename):
        self.file = open(filename, 'a')
        self.output_methods.add('file')

    def set_console_output(self):
        self.output_methods.add('console')

    def set_websocket_output(self, host='localhost', port=8765):
        print(f"Setting up WebSocket output on {host}:{port}")
        self.websocket_url = f"ws://{host}:{port}"
        self.output_methods.add('websocket')
        self.default_connections = {channel: set() for channel in self.channels}
        threading.Thread(target=self._run_websocket_server, daemon=True).start()

    def set_log_level(self, level):
        if isinstance(level, LogLevel):
            self.log_level = level
        elif isinstance(level, str):
            self.log_level = LogLevel[level.upper()]
        else:
            raise ValueError("Invalid log level")

    def _run_websocket_server(self):
        async def handler(websocket, path):
            print(f"New WebSocket connection: {websocket}")
            try:
                init_message = await websocket.recv()
                print(f"Received init message: {init_message}")
                init_data = json.loads(init_message)
                username = init_data.get('username')
                password = init_data.get('password')
                channel = init_data.get('channel', 'default')
                
                if channel not in self.channels:
                    await websocket.send(json.dumps({"status": "invalid_channel"}))
                    return

                if username and password:
                    if self._authenticate(username, password):
                        with self.lock:
                            if username not in self.user_connections:
                                self.user_connections[username] = {}
                            self.user_connections[username][channel] = websocket
                        try:
                            await websocket.send(json.dumps({"status": "authenticated", "channel": channel}))
                            await self._process_queued_messages(username, channel)
                            await websocket.wait_closed()
                        finally:
                            with self.lock:
                                if username in self.user_connections and channel in self.user_connections[username]:
                                    del self.user_connections[username][channel]
                                if username in self.user_connections and not self.user_connections[username]:
                                    del self.user_connections[username]
                    else:
                        print("Connection authentication_failed")
                        await websocket.send(json.dumps({"status": "authentication_failed"}))
                else:
                    with self.lock:
                        print("Add Connection ")
                        self.default_connections[channel].add(websocket)
                    try:
                        await websocket.send(json.dumps({"status": "connected_as_default", "channel": channel}))
                        await self._process_queued_messages(None, channel)
                        await websocket.wait_closed()
                        print("Connection wait_closed")
                    finally:
                        with self.lock:
                            self.default_connections[channel].remove(websocket)
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed")
                pass

        asyncio.set_event_loop(asyncio.new_event_loop())
        start_server = websockets.serve(handler, 'localhost', 8765)
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()

    def _authenticate(self, username, password):
        return username == "user" and password == "password"

    async def _send_websocket(self, message, username=None, channel='default'):
        formatted_message = json.dumps({
            "type": "log",
            "content": message,
            "channel": channel
        })
        with self.lock:
            if username and username in self.user_connections and channel in self.user_connections[username]:
                try:
                    await self.user_connections[username][channel].send(formatted_message)
                except websockets.exceptions.ConnectionClosed:
                    del self.user_connections[username][channel]
                    if not self.user_connections[username]:
                        del self.user_connections[username]
                    await self.message_queue.put((message, username, channel))
            elif channel in self.default_connections and self.default_connections[channel]:
                closed_connections = set()
                for connection in self.default_connections[channel]:
                    try:
                        await connection.send(formatted_message)
                    except websockets.exceptions.ConnectionClosed:
                        closed_connections.add(connection)
                self.default_connections[channel] -= closed_connections
            else:
                await self.message_queue.put((message, username, channel))

    async def _process_queued_messages(self, username, channel):
        while not self.message_queue.empty():
            message, msg_username, msg_channel = await self.message_queue.get()
            if (username is None and msg_username is None and channel == msg_channel) or \
               (username == msg_username and channel == msg_channel):
                await self._send_websocket(message, username, channel)

    def _log(self, level, *args, username=None, channel='default', **kwargs):
        if level.value < self.log_level.value:
            return

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # message = f"[{timestamp}] [{level.name}]" + " ".join(map(str, args))
        message = " ".join(map(str, args))

        if 'console' in self.output_methods:
            color_code = ''
            if level == LogLevel.INFO:
                # color_code = '\033[94m'  # 蓝色
                color_code = '\033[92m'  # 绿色
            elif level == LogLevel.DEBUG:
                color_code = '\033[90m'  # 灰白色
            elif level == LogLevel.WARNING:
                color_code = '\033[33m'  # 黄色
            elif level == LogLevel.ERROR:
                color_code = '\033[31m'  # 红色
            elif level == LogLevel.GREAT:
                color_code = '\033[95m'  # 紫色
            reset_color_code = '\033[0m'  # 恢复默认颜色
            print(color_code + message + reset_color_code, **kwargs)

        if 'file' in self.output_methods and self.file:
            print(color_code + message + reset_color_code, **kwargs)

        if 'websocket' in self.output_methods:
            asyncio.get_event_loop().run_until_complete(self._send_websocket(message, username, channel))

    def debug(self, *args, username=None, channel='default', **kwargs):
        self._log(LogLevel.DEBUG, *args, username=username, channel=channel, **kwargs)

    def info(self, *args, username=None, channel='default', **kwargs):
        self._log(LogLevel.INFO, *args, username=username, channel=channel, **kwargs)

    def warning(self, *args, username=None, channel='default', **kwargs):
        self._log(LogLevel.WARNING, *args, username=username, channel=channel, **kwargs)

    def error(self, *args, username=None, channel='default', **kwargs):
        self._log(LogLevel.ERROR, *args, username=username, channel=channel, **kwargs)

    def great(self, *args, username=None, channel='default', **kwargs):
        self._log(LogLevel.GREAT, *args, username=username, channel=channel, **kwargs)

    def close(self):
        if self.file:
            self.file.close()


# 使用单例实例
SQLOG = SqLog()

# # 主程序示例
# if __name__ == "__main__":
#     SQLOG.set_console_output()
#     SQLOG.set_websocket_output()

#     # 模拟定期发送消息
#     async def send_periodic_message():
#         while True:
#             await asyncio.sleep(5)
#             SQLOG.info("Periodic message")

#     # 运行WebSocket服务器和定期发送消息
#     loop = asyncio.get_event_loop()
#     loop.create_task(send_periodic_message())
#     loop.run_forever()