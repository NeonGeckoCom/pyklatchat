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
    const socket = io(sioServerURL, {transports: ['polling'], extraHeaders: {
        "session": getSessionToken()
    }});

    socket.on('auth_expired', ()=>{
        console.log('Authorization Token expired, refreshing...')
        location.reload();
    });

    socket.on('connect', () => {
         console.info(`Socket IO Connected to Server: ${sioServerURL}`)
    });

    socket.on("connect_error", (err) => {
      console.log(`connect_error due to ${err.message}`);
    });

    socket.on('new_message', async (data) => {
        console.debug('received new_message -> ', data)
        const msgData = JSON.parse(data);
        const preferredLang = getPreferredLanguage(msgData['cid']);
        if (data?.lang !== preferredLang){
            requestTranslation(msgData['cid'], msgData['messageID'], preferredLang);
        }
        await addNewMessage(msgData['cid'], msgData['userID'], msgData['messageID'], msgData['messageText'], msgData['timeCreated'], msgData['repliedMessage'], msgData['attachments'], msgData?.isAudio, msgData?.isAnnouncement)
            .catch(err=>console.error('Error occurred while adding new message: ',err));
        addMessageTransformCallback(msgData['cid'], msgData['messageID'], msgData?.isAudio);
    });

    socket.on('translation_response', async (data) => {
        console.log('translation_response: ', data)
        await applyTranslations(data);
    });

    socket.on('incoming_tts', async (data)=> {
        console.log('received incoming stt audio');
        playTTS(data['cid'], data['lang'], data['audio_data']);
    });

    socket.on('incoming_stt', async (data)=>{
       console.log('received incoming stt response');
       showSTT(data['message_id'], data['lang'], data['message_text']);
    });

    socket.__proto__.emitAuthorized = (event, data) => {
        socket.io.opts.extraHeaders.session = getSessionToken();
        return socket.emit(event, data);
    }

    socket.on('updated_shouts', async (data) =>{
       for (const [cid, shouts] of Object.entries(data)){
           if (isDisplayed(cid)){
               requestTranslation(cid, shouts);
           }
       }
    });

    return socket;
}