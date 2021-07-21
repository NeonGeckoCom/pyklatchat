from chat_server.sio import sio


@sio.event
def connect(sid, environ, auth):
    print(f'{sid} connected')


@sio.event
def disconnect(sid):
    print(f'{sid} disconnected')
