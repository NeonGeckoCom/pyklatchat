let socket;

const sioTriggeringEvents = ['configLoaded', 'configNanoLoaded'];

sioTriggeringEvents.forEach(event=>{
   document.addEventListener(event,(e)=>{
        socket = initSIO();
   });
});

/**
 * Inits socket io client listener by attaching relevant listeners on message channels
 * @return {Socket} Socket IO client instance
 */
function initSIO(){

    const sioServerURL = configData['CHAT_SERVER_URL_BASE'];
    const socket = io(sioServerURL);

    socket.on('connect', () => {
         console.info(`Socket IO Connected to Server: ${sioServerURL}`)
    });

    socket.on('new_message', data => {
        const msgData = JSON.parse(data);
        addMessage(msgData['cid'], msgData['userID'], msgData['messageID'], msgData['messageText'], msgData['timeCreated'], msgData['repliedMessage'],{})
            .catch(err=>console.error('Error occurred while adding new message: ',err));
    });

    return socket;
}