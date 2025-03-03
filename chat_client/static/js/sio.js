let socket;

const sioTriggeringEvents = ['configLoaded', 'configNanoLoaded'];

sioTriggeringEvents.forEach(event=>{
   document.addEventListener(event,_=>{
        socket = initSIO();
   });
});

/**
 * Inits socket io client listener by attaching relevant listeners on message channels
 * @return {Socket} Socket IO client instance
 */
function initSIO(){

    const sioServerURL = configData['CHAT_SERVER_URL_BASE'];

    const socket = io(
        sioServerURL,
        {
            extraHeaders: {
                "session": getSessionToken()
            }
        }
    );

    socket.__proto__.emitAuthorized = (event, data) => {
        socket.io.opts.extraHeaders.session = getSessionToken();
        return socket.emit(event, data);
    }

    socket.on('auth_expired', ()=>{
        if (currentUser && Object.keys(currentUser).length > 0) {
            console.log('Authorization Token expired, refreshing...')
            location.reload();
        }
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
        if (await getCurrentSkin(prompt['cid']) === CONVERSATION_SKINS.PROMPTS) {
            if (!document.getElementById( promptID )) {
                const messageHTML = await buildPromptHTML( prompt );
                messageContainer.insertAdjacentHTML( 'beforeend', messageHTML );
            }
        }
    });

    socket.on('new_message', async (data) => {
        if (await getCurrentSkin(data.cid) === CONVERSATION_SKINS.PROMPTS && data?.prompt_id){
            console.debug('Skipping prompt-related message')
            return
        }
        // console.debug('received new_message -> ', data)
        const preferredLang = getPreferredLanguage(data['cid']);
        if (data?.lang !== preferredLang) {
            requestTranslation(data['cid'], data['messageID']).catch(err => console.error(`Failed to request translation of cid=${data['cid']} messageID=${data['messageID']}: ${err}`));
        }
        addNewMessage(data['cid'], data['userID'], data['messageID'], data['messageText'], data['timeCreated'], data['repliedMessage'], data['attachments'], data?.isAudio, data?.isAnnouncement)
            .then(_=>addMessageTransformCallback(data['cid'], data['messageID'], data?.isAudio))
            .catch(err => console.error('Error occurred while adding new message: ', err));
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
            const winner_response = document.getElementById(`${promptID}_${data['winner']}_resp`).innerText;
            console.log("data:", data)
            promptWinner.innerHTML = await buildPromptWinnerHTML(data['winner'], winner_response);
        }else {
            console.warn(`Failed to get HTML element from prompt_id=${promptID}`);
        }
    });

    socket.on('translation_response', async (data) => {
        console.debug('translation_response: ', data)
        await applyTranslations(data);
    });

    socket.on('subminds_state', async (data) => {
        console.debug('subminds_state: ', data)
        parseSubmindsState(data);
    });

    socket.on('incoming_tts', (data)=> {
        console.debug('received incoming stt audio');
        playTTS(data['cid'], data['lang'], data['audio_data']);
    });

    socket.on('incoming_stt', (data)=>{
       console.debug('received incoming stt response');
       showSTT(data['message_id'], data['lang'], data['message_text']);
    });

    // socket.on('updated_shouts', async (data) =>{
    //     const inputType = data['input_type'];
    //     for (const [cid, shouts] of Object.entries(data['translations'])){
    //        if (await getCurrentSkin(cid) === CONVERSATION_SKINS.BASE){
    //            await requestTranslation(cid, shouts, null, inputType);
    //        }
    //    }
    // });

    return socket;
}
