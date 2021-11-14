let socket;

const sioTriggeringEvents = ['configLoaded', 'configNanoLoaded'];

sioTriggeringEvents.forEach(event=>{
   document.addEventListener(event,(e)=>{
        socket = initSIO();
   });
});


function initSIO(){
    const socket = io("http://"+configData['SOCKET_IO_SERVER_URL']);

    socket.on('connect', () => {
         console.info('Connected to Server')
    });

    socket.on('new_message', data => {
        const msgData = JSON.parse(data);
        addMessage(msgData['cid'], msgData['userID'], msgData['messageID'], msgData['messageText'], msgData['timeCreated'], msgData['repliedMessage'],{})
            .catch(err=>console.error('Error occurred while adding new message: ',err));
    });

    return socket;
}