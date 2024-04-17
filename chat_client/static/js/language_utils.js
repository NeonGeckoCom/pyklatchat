/**
 * Returns preferred language specified in provided cid
 * @param cid: provided conversation id
 * @param inputType: type of the language preference to fetch:
 * "incoming" - for external shouts, "outcoming" - for emitted shouts
 *
 * @return preferred lang by cid or "en"
 */
function getPreferredLanguage(cid, inputType='incoming'){
    let preferredLang = 'en';
    try {
        preferredLang = getChatLanguageMapping(cid, inputType);
    }catch (e) {
        console.warn(`Failed to getChatLanguageMapping - ${e}`)
    }
    return preferredLang;
}

/**
 * Returns preferred language specified in provided cid
 * @param cid: provided conversation id
 * @param lang: new preferred language to set
 * @param inputType: type of the language preference to fetch:
 * @param updateDB: to update user preferences in database
 * @param updateDBOnly: to update user preferences in database only (without translation request)
 * "incoming" - for external shouts, "outcoming" - for emitted shouts
 */
async function setPreferredLanguage(cid, lang, inputType='incoming', updateDB=true, updateDBOnly=false){
    let isOk = false;
    if (updateDB) {
        const formData = new FormData();
        formData.append('lang', lang);
        isOk = await fetchServer(`preferences/update_language/${cid}/${inputType}`,REQUEST_METHODS.POST, formData)
            .then(res => {
                return res.ok;
            });
    } if ((isOk || !updateDB) && !updateDBOnly) {
        updateChatLanguageMapping(cid, inputType, lang);
        const shoutIds = getMessagesOfCID(cid, MESSAGE_REFER_TYPE.ALL, 'plain', true);
        await requestTranslation(cid, shoutIds, lang, inputType);
    }
}

/**
 * Fetches supported languages
 */
async function fetchSupportedLanguages(){
    const query_url = `language_api/settings`;
    return await fetchServer(query_url)
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
 * Sends request for updating target conversation(s) content to the desired language
 * @param cid: conversation id to bound request to
 * @param shouts: list of shout ids to bound request to
 * @param lang: language to apply (defaults to preferred language of each fetched conversation)
 * @param inputType: type of the language input to apply (incoming or outcoming)
 * @param translateToBaseLang: to translate provided items to the system base lang (based on preferred)
 */
async function requestTranslation(cid=null, shouts=null, lang=null, inputType='incoming', translateToBaseLang=false){
    let requestBody = {chat_mapping: {}};
    if(cid && isDisplayed(cid)){
        lang = lang || getPreferredLanguage(cid, inputType);
        if (lang !== 'en' && getMessagesOfCID(cid, MESSAGE_REFER_TYPE.ALL, 'plain').length > 0){
             setChatState(cid, 'updating', 'Applying New Language...');
        }
        if(shouts && !Array.isArray(shouts)){
            shouts = [shouts];
        }
        if (!shouts && inputType){
            shouts = getMessagesOfCID(cid, getMessageReferType(inputType), 'plain', true);
            if (shouts.length === 0){
                console.log(`${cid} yet has no shouts matching type=${inputType}`);
                setChatState(cid, 'active');
                return
            }
        }
        setDefault(requestBody.chat_mapping, cid, {});
        requestBody.chat_mapping[cid] = {'lang': lang, 'shouts': shouts || []}
        if (translateToBaseLang){
            requestBody.chat_mapping[cid]['source_lang'] = getPreferredLanguage(cid);
        }
    }else{
        requestBody.chat_mapping = getChatLanguageMapping();
        if (!requestBody.chat_mapping){
            console.log('Chat mapping is undefined - returning');
            return
        }
    }
    requestBody['user'] = currentUser['_id'];
    requestBody['inputType'] = inputType;
    console.debug(`requestBody = ${JSON.stringify(requestBody)}`);
    socket.emitAuthorized('request_translate', requestBody);
}

/**
 * Sets selected language to the target language selector
 * @param clickedItem: Language selector element clicked
 * @param cid: target conversation id
 * @param inputType: type of the language input to apply (incoming or outcoming)
 */
async function setSelectedLang(clickedItem, cid, inputType="incoming"){
    const selectedLangNode = document.getElementById(`language-selected-${cid}-${inputType}`);
    const selectedLangList = document.getElementById(`language-list-${cid}-${inputType}`);

    // console.log('emitted lang update')
    const preferredLang = getPreferredLanguage(cid, inputType);
    const preferredLangProps = configData['supportedLanguages'][preferredLang];
    const newKey = clickedItem.getAttribute('data-lang');
    const newPreferredLangProps = configData['supportedLanguages'][newKey];

    const direction = inputType === 'incoming'?'down':'up';
    selectedLangNode.innerHTML = await buildHTMLFromTemplate('selected_lang', {'key': newKey, 'name': newPreferredLangProps['name'], 'icon': newPreferredLangProps['icon'], 'direction': direction})
    if (preferredLangProps) {
        selectedLangList.getElementsByClassName('lang-container')[0].insertAdjacentHTML('beforeend', await buildLangOptionHTML(cid, preferredLang, preferredLangProps['name'], preferredLangProps['icon'], inputType));
    }
    else{
        console.warn(`"${preferredLang}" is set to be preferred but currently not supported`)
    }
    if (clickedItem.parentNode){
        clickedItem.parentNode.removeChild(clickedItem);
    }
    console.log(`cid=${cid};new preferredLang=${newKey}, inputType=${inputType}`);
    await setPreferredLanguage(cid, newKey, inputType, true);
    const insertedNode = document.getElementById(getLangOptionID(cid, preferredLang, inputType));
    insertedNode.addEventListener('click', async (e)=> {
        e.preventDefault();
        await setSelectedLang(insertedNode, cid, inputType);
    });
}

/**
 * Initialize language selector for conversation
 * @param cid: target conversation id
 * @param inputType: type of the language input to apply (incoming or outcoming)
 */
async function initLanguageSelector(cid, inputType="incoming"){
   let preferredLang = getPreferredLanguage(cid, inputType);
   const supportedLanguages = configData['supportedLanguages'];
   if (!supportedLanguages.hasOwnProperty(preferredLang)){
       preferredLang = 'en';
   }
   const selectedLangNode = document.getElementById(`language-selected-${cid}-${inputType}`);
   const langList = document.getElementById(`language-list-${cid}-${inputType}`);
   if (langList) {
       const langListContainer = langList.getElementsByClassName('lang-container')[0]

       if (langListContainer) {
           langListContainer.innerHTML = "";
       }

       // selectedLangNode.innerHTML = "";
       for (const [key, value] of Object.entries(supportedLanguages)) {

           if (key === preferredLang) {
               const direction = inputType === 'incoming' ? 'down' : 'up';
               selectedLangNode.innerHTML = await buildHTMLFromTemplate('selected_lang',
                   {'key': key, 'name': value['name'], 'icon': value['icon'], 'direction': direction})
           } else {
               langListContainer.insertAdjacentHTML('beforeend', await buildLangOptionHTML(cid, key, value['name'], value['icon'], inputType));
               const itemNode = document.getElementById(getLangOptionID(cid, key, inputType));
               itemNode.addEventListener('click', async (e) => {
                   e.preventDefault();
                   await setSelectedLang(itemNode, cid, inputType)
               });
           }
       }
   }
}

/**
 * Inits both incoming and outcoming language selectors
 * @param cid: target conversation id
 */
const initLanguageSelectors = async (cid) => {
    for (const inputType of ['incoming', 'outcoming']){
        await initLanguageSelector(cid, inputType);
    }
}


function getMessageReferType(inputType){
    return inputType === 'incoming'?MESSAGE_REFER_TYPE.OTHERS: MESSAGE_REFER_TYPE.MINE;
}


/**
 * Sends request to server for chat language refreshing
 */
async function requestChatsLanguageRefresh(){
    const languageMapping = currentUser?.preferences?.chat_language_mapping || {};
    console.log(`languageMapping=${JSON.stringify(languageMapping)}`)
    for (const [cid, value] of Object.entries(languageMapping)) {
        if (isDisplayed(cid)) {
            for (const inputType of ['incoming', 'outcoming']) {
                const lang = value[inputType] || 'en';
                if (lang !== 'en') {
                    await setPreferredLanguage(cid, lang, inputType, false);
                }
            }
        }
    }
    console.log(`chatLanguageMapping=${JSON.stringify(getChatLanguageMapping())}`)
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
    const inputType = setDefault(data, 'input_type', 'incoming');
    for (const [cid, messageTranslations] of Object.entries(data['translations'])) {

        if(!isDisplayed(cid)){
            console.log(`cid=${cid} is not displayed, skipping translations population`)
            continue;
        }

        setChatState(cid, 'active');

        console.debug(`Fetching translation of ${cid}`);
        // console.debug(`translations=${JSON.stringify(messageTranslations)}`)

        const messageTranslationsShouts = messageTranslations['shouts'];
        if (messageTranslationsShouts) {
            const messageReferType = getMessageReferType(inputType);
            const messages = getMessagesOfCID(cid, messageReferType, 'plain');
            Array.from(messages).forEach(message => {
                const messageID = message.id;
                let repliedMessage = null;
                let repliedMessageID = null;
                try {
                    repliedMessage = message.getElementsByClassName('reply-placeholder')[0].getElementsByClassName('reply-text')[0];
                    repliedMessageID = repliedMessage.getAttribute('data-replied-id')
                    // console.debug(`repliedMessageID=${repliedMessageID}`)
                } catch (e) {
                    // console.debug(`replied message not found for ${messageID}`);
                }
                if (messageID in messageTranslationsShouts) {
                    message.getElementsByClassName('message-text')[0].innerHTML = messageTranslationsShouts[messageID];
                }
                if (repliedMessageID && repliedMessageID in messageTranslationsShouts) {
                    repliedMessage.innerHTML = messageTranslationsShouts[repliedMessageID];
                }
            });
            await initLanguageSelector(cid, inputType);
        }
    }
}


const getChatLanguageMapping = (cid=null, inputType=null) => {
    let res =  setDefault(setDefault(currentUser, 'preferences', {}), 'chat_language_mapping', {});
    if (cid){
        res = setDefault(res, cid, {});
    }if (inputType){
        res = setDefault(res, inputType, 'en');
    }
    return res;
}

const updateChatLanguageMapping = (cid, inputType, lang) => {
    setDefault(currentUser.preferences.chat_language_mapping, cid, {})[inputType] = lang;
    console.log(`cid=${cid},inputType=${inputType} updated to lang=${lang}`);
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
