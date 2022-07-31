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

    socket.on("connect_error", (err) => {
      console.log(`connect_error due to ${err.message}`);
    });

    socket.on('new_message', (data) => {
        console.log('new_message: ', data)
        const msgData = JSON.parse(data);
        sendLanguageUpdateRequest();
        addMessage(msgData['cid'], msgData['userID'], msgData['messageID'], msgData['messageText'], msgData['timeCreated'], msgData['repliedMessage'], msgData['attachments'], !!msgData?.isAudio)
            .catch(err=>console.error('Error occurred while adding new message: ',err));
    });

    socket.on('translation_response', async (data) => {
        console.log('translation_response: ', data)
        await applyTranslations(data);
    });

    socket.on('incoming_tts', async (data)=> {
        console.log('received incoming stt audio');
        playTTS(data['cid'], data['lang'], data['audio_data']);
    });

    return socket;
}