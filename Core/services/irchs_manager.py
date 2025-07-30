from twisted.internet.protocol import ClientFactory
from twisted.internet import reactor, defer
from twisted.words.protocols import irc
from socketio import AsyncClient
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MIDDLE_CON = AsyncClient(
    reconnection=True,
    reconnection_attempts=5,
    reconnection_delay=1,
    reconnection_delay_max=5,
    logger=True, #disable later
)
ROOMS_PER_SERVER = 100

class IRCHServer(irc.IRCClient):
    def __init__(self, preloaded_rooms):
        self.preloaded_rooms = preloaded_rooms
        self.username = f"paroot_{os.urandom(4).hex()}"
        self.nickname = f"PARoot!_{os.urandom(4).hex()}"

    def connectionMade(self):
        self.setUserInfo(self.nickname, self.username, f"PAROOT 30.07.2025")
        irc.IRCClient.connectionMade(self)
        logger.info(f"IRCHS has connected to the IRC provider")

    def signedOn(self):
        logger.info(f"IRCHS has signed on the IRC provider")
        reactor.callLater(0, self.rejoin_rooms)

    def rejoin_rooms(self):
        def rejoin_in_batches(rooms):
            if rooms is None: return
            batch = rooms[:self.load_batch_size]
            self.join(','.join(batch))
            logger.info(f"IRCHS has siccessfully rejoined channels: {', '.join(batch)}")
            channels_left = rooms[self.load_batch_size:]
            if channels_left is not None:
                reactor.callLater(self.load_batch_delay, rejoin_in_batches, channels_left)
        rejoin_in_batches(self.preloaded_rooms)

    def privmsg(self, user, room, message):
        username = user.split('!')[1].split('@')[0] if '!' in user and '@' in user else 'unknown'
        room_id = room.replace('#', '')
        if room_id is not None:
            MIDDLE_CON.emit('irc_message', {
                "room_id": room_id,
                "username": username,
                "content": message,
            })
        else: logger.error(f"IRCHS received a message from {user} in an unknown room: {room}")

    def noticed(self, user, room, message):
        if user.startswith('NickServ'):
            status = 'successfully registered' in message or 'You are now identified' in message
            MIDDLE_CON.emit('irc_auth_status', {
                "status": status,
                "content": message, #Maybe not required??
            })

    def connectionLost(self, reason):
        logger.error(f"IRCHS lost connection to the IRC provider: {reason}")

class IRCHServerFactory(ClientFactory):
    def __init__(self, preloaded_rooms, load_batch_size: int = 10, load_batch_delay: int = 2):
        self.preloaded_rooms = preloaded_rooms
        self.load_batch_size = load_batch_size
        self.load_batch_delay = load_batch_delay

    def buildProtocol(self, addr):  
        pr = IRCHServer(self.preloaded_rooms)
        pr.factory = self
        return pr
    
    def clientConnectionFailed(self, _, reason):
        logger.error(f"IRCHSF connection to IRC provider failed: {reason}")
        reactor.stop()

def setup(rooms):
    nors = (len(rooms) + ROOMS_PER_SERVER - 1) // ROOMS_PER_SERVER #number of reqired servers
    for _ in range(nors):
        delegated_rooms = rooms[_ * ROOMS_PER_SERVER:(_ + 1) * ROOMS_PER_SERVER]
        factory = IRCHServerFactory(_, delegated_rooms)
        reactor.connectTCP("irc.libera.chat", 6667, factory)

@MIDDLE_CON.event
async def connect():
    logger.info("IRCHS manager has successfully connected to the CORE")

@MIDDLE_CON.event
async def connect_error(data):
    logger.error(f"IRCHS manager connection error: {data}")

@MIDDLE_CON.event
async def disconnect():
    logger.info("IRCHS manager disconnected from CORE")

@MIDDLE_CON.event
async def send_message(data): #Will change later
    for server in reactor.getReaders():
        if isinstance(server, IRCHServer):
            server.msg(f"#{data.room_id}", f"[{data.nickname}] {data.content}")
            break
    else:
        servers = [_ for _ in reactor.getReaders() if isinstance(_, IRCHServer)]
        if servers:
            servers[0].msg(f"#{data.room_id}", f"[{data.nickname}] {data.content}")

@MIDDLE_CON.event
async def join_channel(data):
    channel = data['channel']
    for client in reactor.getReaders():
        if isinstance(client, IRCClient) and len(client.channels) < CHANNELS_PER_CLIENT:
            client.join(channel)
            client.channels.append({'id': len(load_channels()), 'name': channel})
            client.channel_map.set(channel, len(load_channels()) - 1)
            await sio.emit('irc_message', {
                'client_id': client.client_id,
                'channel_id': len(load_channels()) - 1,
                'channel': channel,
                'nick': 'System',
                'username': 'system',
                'message': f"You joined {channel}",
                'timestamp': datetime.utcnow().isoformat()
            }, room=channel)
            channels = load_channels()
            if not any(ch['name'] == channel for ch in channels):
                channels.append({'id': len(channels), 'name': channel})
                save_channels(channels)
            break
    else:
        clients = [c for c in reactor.getReaders() if isinstance(c, IRCClient)]
        if clients:
            clients[0].join(channel)
            clients[0].channels.append({'id': len(load_channels()), 'name': channel})
            clients[0].channel_map.set(channel, len(load_channels()) - 1)
            await sio.emit('irc_message', {
                'client_id': clients[0].client_id,
                'channel_id': len(load_channels()) - 1,
                'channel': channel,
                'nick': 'System',
                'username': 'system',
                'message': f"You joined {channel}",
                'timestamp': datetime.utcnow().isoformat()
            }, room=channel)
            channels = load_channels()
            if not any(ch['name'] == channel for ch in channels):
                channels.append({'id': len(channels), 'name': channel})
                save_channels(channels)

@sMIDDLE_CON.event
async def register(data):
    clients = [c for c in reactor.getReaders() if isinstance(c, IRCClient)]
    if clients:
        clients[0].setNick(data['nickname'])
        clients[0].msg('NickServ', f"REGISTER {data['password']} user@example.com")

@MIDDLE_CON.event
async def login(data):
    clients = [c for c in reactor.getReaders() if isinstance(c, IRCClient)]
    if clients:
        clients[0].setNick(data['nickname'])
        clients[0].msg('NickServ', f"IDENTIFY {data['password']}")

def start():
    channels = load_channels()
    setup_clients(channels)
    reactor.callLater(0, lambda: asyncio.ensure_future(sio.connect('http://localhost:8000')))
    reactor.run()