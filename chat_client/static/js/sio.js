document.addEventListener('configLoaded',(e)=>{

    const socket = io("http://"+configData['SOCKET_IO_SERVER_URL']);

    socket.on('connect', () => {
         console.info('Connected to Server')
    });

    socket.on('new_message', data => {
        console.log(data);
        const msgData = JSON.parse(data);
        addMessage(msgData['cid'], msgData['userID'], msgData['messageText'], msgData['timeCreated'], {})
            .catch(err=>console.error('Error occurred while adding new message: ',err));
    });
});