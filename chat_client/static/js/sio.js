const socket = io("http://127.0.0.1:8000");

socket.on('connect', () => {
     console.info('Connected to Server')
});

socket.on('user_message', (msg) => {
    const msgData = JSON.parse(msg);
    addMessage(msgData['cid'], msgData['userID'], msgData['messageText'], msgData['timeCreated'], {}, false);
});