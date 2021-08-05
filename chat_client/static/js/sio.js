const socket = io("http://127.0.0.1:8000");

socket.on('connect', () => {
     console.info('Connected to Server')
});

socket.on('new_message', data => {
    console.log(data);
    const msgData = JSON.parse(data);
    addMessage(msgData['cid'], msgData['userID'], msgData['messageText'], msgData['timeCreated'], {}, false);
});