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

    socket.on('new_prompt_created', async (prompt) => {
        const messageContainer = getMessageListContainer(prompt['cid']);
        const promptID = prompt['_id'];
        if (!document.getElementById(promptID)){
            const messageHTML = await buildPromptHTML(prompt);
            messageContainer.insertAdjacentHTML('beforeend', messageHTML);
        }
    });

    socket.on('new_message', async (data) => {
        console.debug('received new_message -> ', data)
        const msgData = JSON.parse(data);
        const skin = getCIDStoreProperty(msgData['cid'], 'skin');
        if (skin === CONVERSATION_SKINS.BASE) {
            const preferredLang = getPreferredLanguage(msgData['cid']);
            if (data?.lang !== preferredLang) {
                await requestTranslation(msgData['cid'], msgData['messageID']);
            }
            await addNewMessage(msgData['cid'], msgData['userID'], msgData['messageID'], msgData['messageText'], msgData['timeCreated'], msgData['repliedMessage'], msgData['attachments'], msgData?.isAudio, msgData?.isAnnouncement)
                .catch(err => console.error('Error occurred while adding new message: ', err));
            addMessageTransformCallback(msgData['cid'], msgData['messageID'], msgData?.isAudio);
        }
    });

    socket.on('new_prompt_message', async (message) => {
        await addPromptMessage(message['cid'], message['userID'], message['messageText'], message['promptID'], message['promptState'])
                .catch(err => console.error('Error occurred while adding new prompt data: ', err));
    });

    socket.on('set_prompt_completed', async (data) => {
        const promptID = data['prompt_id'];
        const promptElem = document.getElementById(promptID);
        console.info(`setting prompt_id=${promptID} as completed`);
        if (promptElem){
            const promptWinner = document.getElementById(`${promptID}_winner`);
            promptWinner.innerText = getPromptWinnerText(data['winner']);
        }else {
            console.warn(`Failed to get HTML element from prompt_id=${promptID}`);
        }
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
        const inputType = data['input_type'];
        for (const [cid, shouts] of Object.entries(data['translations'])){
           if (isDisplayed(cid) && getCIDStoreProperty(cid, 'skin') === CONVERSATION_SKINS.BASE){
               await requestTranslation(cid, shouts, null, inputType);
           }
       }
    });

    return socket;
}