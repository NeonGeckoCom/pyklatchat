/**
 * Object representing loaded HTML components mapping:
 * - key: component name,
 * - value: HTML template that should be populated with actual data)
 * @type Object
 */
let loadedComponents = {}

/**
 * Fetches template context into provided html template
 * @param html: HTML template
 * @param templateContext: object containing context to fetch
 * @return {string} HTML with fetched context
 */
function fetchTemplateContext(html, templateContext){
    for (const [key, value] of Object.entries(templateContext)) {
        html = html.replaceAll('{'+key+'}', value);
    }
    return html;
}

/**
 * Builds HTML from passed params and template name
 * @param templateName: name of the template to fetch
 * @param templateContext: properties from template to fetch
 * @param requestArgs: request string arguments (optional)
 * @returns built template string
 */
async function buildHTMLFromTemplate(templateName, templateContext = {}, requestArgs=''){
    if(!configData['DISABLE_CACHING'] && loadedComponents.hasOwnProperty(templateName) && !requestArgs){
        const html = loadedComponents[templateName];
        return fetchTemplateContext(html, templateContext);
    }else {
        return await fetch(`${configData['currentURLBase']}/components/${templateName}?${requestArgs}`)
            .then((response) => {
                if (response.ok) {
                    return response.text();
                }
                throw `template unreachable (HTTP STATUS:${response.status}: ${response.statusText})`
            })
            .then((html) => {
                if (!(configData['DISABLE_CACHING'] || loadedComponents.hasOwnProperty(templateName) || requestArgs)) {
                    loadedComponents[templateName] = html;
                }
                return fetchTemplateContext(html, templateContext);
            }).catch(err => console.warn(`Failed to fetch template for ${templateName}: ${err}`));
    }
}


/**
 * Get Node id based on language key
 * @param cid: desired conversation id
 * @param key: language key (e.g. 'en')
 * @return {string} ID of Node
 */
function getLangOptionID(cid, key){
    return `language-option-${cid}-${key}`;
}

/**
 * Build language selection HTML based on provided params
 * @param cid: desired conversation id
 * @param key: language key (e.g 'en')
 * @param name: name of the language (e.g. English)
 * @param icon: language icon (refers to flag-icon specs)
 * @return {string} formatted langSelectPattern
 */
async function buildLangOptionHTML(cid, key, name, icon){
    return await buildHTMLFromTemplate('lang_option', {
        'itemId': getLangOptionID(cid, key),
        'key': key,
        'name': name,
        'icon': icon
    })
}

/**
 * Builds user message HTML
 * @param userData: data of message sender
 * @param messageID: id of user message
 * @param messageText: text of user message
 * @param timeCreated: date of creation
 * @param isMine: if message was emitted by current user
 * @param isAudio: if message is audio message (defaults to '0')
 * @param isAnnouncement: is message if announcement (defaults to '0')
 * @returns {string}: constructed HTML out of input params
 */
async function buildUserMessageHTML(userData, messageID, messageText, timeCreated, isMine, isAudio = '0', isAnnouncement = '0'){
    const messageTime = getTimeFromTimestamp(timeCreated);
    let imageComponent;
    let shortedNick = `${userData['nickname'][0]}${userData['nickname'][userData['nickname'].length - 1]}`;
    if (userData.hasOwnProperty('avatar') && userData['avatar']){
        imageComponent = `<img alt="${shortedNick}" onerror="handleImgError(this);" src="${configData["CHAT_SERVER_URL_BASE"]}/users_api/${userData['_id']}/avatar">`
    }
    else{
        imageComponent = `<p>${userData['nickname'][0]}${userData['nickname'][userData['nickname'].length - 1]}</p>`;
    }
    const messageClass = isAnnouncement === '1'?'announcement':isMine?'in':'out';
    const templateName = isAudio === '1'?'user_message_audio': 'user_message';
    return await buildHTMLFromTemplate(templateName,
        {'message_class': messageClass,
            'is_announcement': isAnnouncement,
            'image_component': imageComponent,
            'message_id':messageID,
            'nickname': userData['nickname'],
            'message_text':messageText,
            'audio_url': `${configData["CHAT_SERVER_URL_BASE"]}/files/get_audio/${messageID}`,
            'message_time': messageTime});
}

/**
 * Gets user message HTML from received message data object
 * @param message: Message Object received
 * @return {Promise<string>} HTML by the provided message data
 */
async function messageHTMLFromData(message){
    const isMine = currentUser && message['user_nickname'] === currentUser['nickname'];
    return buildUserMessageHTML({
            'avatar': message['user_avatar'],
            'nickname': message['user_nickname'],
            '_id': message['user_id']
        },
        message['message_id'],
        message['message_text'],
        message['created_on'],
        isMine,
        message?.is_audio,
        message?.is_announcement);
}

/**
 * Builds HTML for received conversation data
 * @param conversationData: JS Object containing conversation data of type:
 * {
 *     '_id': 'id of conversation',
 *     'conversation_name': 'title of the conversation',
 *     'chat_flow': [{
 *         'user_nickname': 'nickname of sender',
 *         'user_avatar': 'avatar of sender',
 *         'message_id': 'id of the message',
 *         'message_text': 'text of the message',
 *         'created_on': 'creation time of the message'
 *     }, ... (num of user messages returned)]
 * }
 * @returns {string} conversation HTML based on provided data
 */
async function buildConversationHTML(conversationData = {}){
    const cid = conversationData['_id'];
    const conversation_name = conversationData['conversation_name'];
    let chatFlowHTML = "";
    if(conversationData.hasOwnProperty('chat_flow')) {
        for (const message of Array.from(conversationData['chat_flow'])) {
            chatFlowHTML += await messageHTMLFromData(message);
            addConversationParticipant(conversationData['_id'], message['user_nickname']);
        }
    }else{
        chatFlowHTML+=`<div class="blank_chat">No messages in this chat yet...</div>`;
    }
    return await buildHTMLFromTemplate('conversation',
        {'cid': cid, 'conversation_name':conversation_name, 'chat_flow': chatFlowHTML});
}
