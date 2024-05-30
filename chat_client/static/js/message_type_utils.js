/**
 * Adds speaking callback for the message
 * @param cid: id of the conversation
 * @param messageID: id of the message
 */
function addTTSCallback(cid, messageID){
    const speakingButton = document.getElementById(`${messageID}_speak`);
    if (speakingButton) {
        speakingButton.addEventListener('click', (e) => {
            e.preventDefault();
            getTTS(cid, messageID, getPreferredLanguage(cid));
            setChatState(cid, 'updating', `Fetching TTS...`)
        });
    }
}

/**
 * Adds speaking callback for the message
 * @param cid: id of the conversation
 * @param messageID: id of the message
 */
function addSTTCallback(cid, messageID){
    const sttButton = document.getElementById(`${messageID}_text`);
    if (sttButton) {
        sttButton.addEventListener('click', (e) => {
            e.preventDefault();
            const sttContent = document.getElementById(`${messageID}-stt`);
            if (sttContent){
                sttContent.innerHTML = `<div class="text-center">
                                        Waiting for STT...  <div class="spinner-border spinner-border-sm" role="status">
                                                            <span class="sr-only">Loading...</span>
                                                        </div>
                                        </div>`;
                sttContent.style.setProperty('display', 'block', 'important');
                getSTT(cid, messageID, getPreferredLanguage(cid));
            }
        });
    }
}

/**
 * Attaches STT capabilities for audio messages and TTS capabilities for text messages
 * @param cid: parent conversation id
 * @param messageID: target message id
 * @param isAudio: if its an audio message (defaults to '0')
 */
function addMessageTransformCallback(cid, messageID, isAudio='0'){
    if (isAudio === '1'){
        addSTTCallback(cid, messageID);
    }else{
        addTTSCallback(cid, messageID);
    }
}


/**
 * Attaches STT capabilities for audio messages and TTS capabilities for text messages
 * @param conversationData: conversation data object
 */
function addCommunicationChannelTransformCallback(conversationData) {
    if (conversationData.hasOwnProperty('chat_flow')) {
        getUserMessages(conversationData).forEach(message => {
            addMessageTransformCallback(conversationData['_id'], message['message_id'], message?.is_audio);
        });
    }
}
