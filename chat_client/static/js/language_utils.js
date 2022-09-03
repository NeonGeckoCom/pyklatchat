/**
 * Returns preferred language specified in provided cid
 * @param cid: provided conversation id
 *
 * @return preferred lang by cid or "en"
 */
function getPreferredLanguage(cid){
    let preferredLang;
    try {
        preferredLang = configData['chatLanguageMapping'][cid]['lang'];
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
    } if(!configData['chatLanguageMapping'].hasOwnProperty(cid)){
        configData['chatLanguageMapping'][cid] = {};
    }
    configData['chatLanguageMapping'][cid]['lang'] = lang;
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
    let requestBody = {chat_mapping: {}};
    if(cid && getOpenedChats().includes(cid)){
        setChatState(cid, 'updating', 'Applying New Language...');
        const preferredLang = getPreferredLanguage(cid)
        if(shouts && !Array.isArray(shouts)){
            shouts = [shouts];
        }
        requestBody.chat_mapping[cid] = {'lang': lang || preferredLang, 'shouts': shouts || []}
    }else{
        requestBody.chat_mapping = configData['chatLanguageMapping'];
    }
    requestBody['user'] = currentUser['_id'];
    console.debug(`requestBody = ${JSON.stringify(requestBody)}`);
    socket.emit('request_translate', requestBody);
}

async function setSelectedLang(clickedItem, cid){
    const selectedLangNode = document.getElementById(`language-selected-${cid}`);
    const selectedLangList = document.getElementById(`language-list-${cid}`);

    // console.log('emitted lang update')
    const preferredLang = getPreferredLanguage(cid);
    const preferredLangProps = configData['supportedLanguages'][preferredLang];
    const newKey = clickedItem.getAttribute('data-lang');
    const newPreferredLangProps = configData['supportedLanguages'][newKey];
    selectedLangNode.innerHTML = await buildHTMLFromTemplate('selected_lang', {'key': newKey, 'name': newPreferredLangProps['name'], 'icon': newPreferredLangProps['icon']})
    selectedLangList.insertAdjacentHTML('beforeend', await buildLangOptionHTML(cid, preferredLang, preferredLangProps['name'], preferredLangProps['icon']));
    clickedItem.parentNode.removeChild(clickedItem);
    console.log(`cid=${cid};new preferredLang=${newKey}`)
    setPreferredLanguage(cid, newKey);
    const insertedNode = document.getElementById(getLangOptionID(cid, preferredLang));
    sendLanguageUpdateRequest(cid, null, newKey);
    insertedNode.addEventListener('click', async (e)=> {
        e.preventDefault();
        await setSelectedLang(insertedNode, cid);
    });
}

/**
 * Initialize language selector for conversation
 * @param cid: target conversation id
 */
async function initLanguageSelector(cid){
   let preferredLang = getPreferredLanguage(cid);
   const supportedLanguages = configData['supportedLanguages'];
   if (!supportedLanguages.hasOwnProperty(preferredLang)){
       preferredLang = 'en';
   }
   const selectedLangNode = document.getElementById(`language-selected-${cid}`);
   const selectedLangList = document.getElementById(`language-list-${cid}`);

   if (selectedLangList){
      selectedLangList.innerHTML = "";
   }
   // selectedLangNode.innerHTML = "";
   for (const [key, value] of Object.entries(supportedLanguages)) {

      if (key === preferredLang){
          selectedLangNode.innerHTML = await buildHTMLFromTemplate('selected_lang',
              {'key': key, 'name': value['name'], 'icon': value['icon']})
      }else{
          selectedLangList.insertAdjacentHTML('beforeend', await buildLangOptionHTML(cid, key, value['name'], value['icon']));
          const itemNode = document.getElementById(getLangOptionID(cid, key));
          itemNode.addEventListener('click', async (e)=>{
              e.preventDefault();
              await setSelectedLang(itemNode, cid)
          });
      }
   }
}


/**
 * Sends request to server for chat language refreshing
 */
function requestChatsLanguageRefresh(){
    const languageMapping = currentUser?.preferences?.chat_languages || {};
    console.log(`languageMapping=${JSON.stringify(languageMapping)}`)
    configData['chatLanguageMapping'] = {}
    for (const [key, value] of Object.entries(languageMapping)) {
        configData['chatLanguageMapping'][key] = {'lang': value || 'en'};
    }
    console.log(`chatLanguageMapping=${JSON.stringify(configData['chatLanguageMapping'])}`)
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
async function applyTranslations(data){
    for (const [cid, messageTranslations] of Object.entries(data)) {

        if(!isDisplayed(cid)){
            console.log(`cid=${cid} is not displayed, skipping translations population`)
            continue;
        }

        setChatState(cid, 'active');

        console.debug(`Fetching translation of ${cid}`);
        // console.debug(`translations=${JSON.stringify(messageTranslations)}`)

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
        await initLanguageSelector(cid);
    }
}

/**
 * Custom Event fired on supported languages init
 * @type {CustomEvent<string>}
 */
const supportedLanguagesLoadedEvent = new CustomEvent("supportedLanguagesLoaded", { "detail": "Event that is fired when system supported languages are loaded" });

document.addEventListener('DOMContentLoaded', (_)=>{
    document.addEventListener('configLoaded',async (_)=>{
        await fetchSupportedLanguages().then(_ => document.dispatchEvent(supportedLanguagesLoadedEvent));
    });
});