/**
 * Returns preferred language specified in provided cid
 * @param cid: provided conversation id
 *
 * @return preferred lang by cid or "en"
 */
function getPreferredLanguage(cid){
    let preferredLang;
    try {
        preferredLang = configData['chatLanguageMapping'][cid];
    }catch {
        preferredLang = 'en'
    }
    return preferredLang || 'en';
}

/**
 * Returns preferred language specified in provided cid
 * @param cid: provided conversation id
 * @param lang: new preferred language to set
 */
function setPreferredLanguage(cid, lang){
    if (!configData.hasOwnProperty('chatLanguageMapping')){
        configData['chatLanguageMapping'] = {};
    }configData['chatLanguageMapping'][cid] = lang;
}

/**
 * Fetches supported languages
 */
async function fetchSupportedLanguages(){
    const query_url = `${configData['CHAT_SERVER_URL_BASE']}/language_api/settings`;
    return await fetch(query_url)
            .then(response => {
                if(response.ok){
                    return response.json();
                }else{
                    console.log(`failed to fetch supported languages - ${response.statusText}`)
                    throw response.statusText;
                }
            })
            .then(data => {
                configData['supportedLanguages'] = data['supported_languages'];
                console.info(`supported languages updated - ${JSON.stringify(configData['supportedLanguages'])}`)
            }).catch(err=> console.warn('Failed to fulfill request due to error:',err));
}

/**
 * Sends request for updating target cids content to the desired language
 */
function sendLanguageUpdateRequest(cid=null, shouts=null, lang=null){
    let requestBody = configData['chatLanguageMapping'];
    if(cid && getOpenedChats().includes(cid)){
        const preferredLang = getPreferredLanguage(cid)
        requestBody = {}
        if(shouts && !Array.isArray(shouts)){
            shouts = [shouts];
        }
        requestBody[cid] = {'lang': lang || preferredLang, 'shouts': shouts || []}
    }
    console.log(`chatLanguageMapping = ${JSON.stringify(requestBody)}`);
    socket.emit('request_translate', requestBody);
}


/**
 * Sends request to server for chat language refreshing
 */
function requestChatsLanguageRefresh(){
    const languageMapping = currentUser?.preferences?.chat_languages || {};
    const displayedCIDs = getOpenedChats();
    configData['chatLanguageMapping'] = {}
    Array.from(displayedCIDs).forEach(cid => {
        configData['chatLanguageMapping'][cid] = {'lang': languageMapping[cid] || 'en'};
    });
    sendLanguageUpdateRequest();
}

/**
 * Applies translation based on received data
 * @param data: translation object received
 * Note: data should be of format:
 * {
 *     'cid': {'message1':'translation of message 1',
 *             'message2':'translation of message 2'}
 * }
 */
function applyTranslations(data){
    for (const [cid, messageTranslations] of Object.entries(data)) {

        console.log(`Fetching translation of ${cid}`);
        console.debug(`translations=${JSON.stringify(messageTranslations)}`)

        const messageTranslationsShouts = messageTranslations['shouts']
        const messages = getMessagesOfCID(cid);
        Array.from(messages).forEach(message => {
            const messageID = message.id;
            let repliedMessage = null;
            let repliedMessageID = null;
            try {
                repliedMessage = message.getElementsByClassName('reply-placeholder')[0].getElementsByClassName('reply-text')[0];
                repliedMessageID = repliedMessage.getAttribute('data-replied-id')
                // console.debug(`repliedMessageID=${repliedMessageID}`)
            }catch (e) {
                // console.debug(`replied message not found for ${messageID}`);
            }
            if (messageID in messageTranslationsShouts){
                message.getElementsByClassName('message-text')[0].innerHTML = messageTranslationsShouts[messageID];
            }
            if (repliedMessageID && repliedMessageID in messageTranslationsShouts){
                repliedMessage.innerHTML = messageTranslationsShouts[repliedMessageID];
            }
        });
    }
}

/**
 * Custom Event fired on supported languages init
 * @type {CustomEvent<string>}
 */
const supportedLanguagesLoadedEvent = new CustomEvent("supportedLanguagesLoaded", { "detail": "Event that is fired when system supported languages are loaded" });

document.addEventListener('DOMContentLoaded', (e)=>{
    document.addEventListener('chatAlignmentRestored',async (e)=>{
        await fetchSupportedLanguages().then(r => document.dispatchEvent(supportedLanguagesLoadedEvent));
    });
});