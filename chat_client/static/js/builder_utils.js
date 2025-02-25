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
 * @param inputType: type of the language input to apply (incoming or outcoming)
 * @return {string} ID of Node
 */
function getLangOptionID(cid, key, inputType='incoming'){
    return `language-option-${cid}-${inputType}-${key}`;
}

/**
 * Build language selection HTML based on provided params
 * @param cid: desired conversation id
 * @param key: language key (e.g 'en')
 * @param name: name of the language (e.g. English)
 * @param icon: language icon (refers to flag-icon specs)
 * @param inputType: type of the language input to apply (incoming or outcoming)
 * @return {string} formatted langSelectPattern
 */
async function buildLangOptionHTML(cid, key, name, icon, inputType){
    return await buildHTMLFromTemplate('lang_option', {
        'itemId': getLangOptionID(cid, key, inputType),
        'key': key,
        'name': name,
        'icon': icon
    })
}

/**
 * Builds user message HTML
 * @param userData: data of message sender
 * @param cid: conversation id of target message
 * @param messageID: id of user message
 * @param messageText: text of user message
 * @param timeCreated: date of creation
 * @param isMine: if message was emitted by current user
 * @param isAudio: if message is audio message (defaults to '0')
 * @param isAnnouncement: is message if announcement (defaults to '0')
 * @returns {string}: constructed HTML out of input params
 */
async function buildUserMessageHTML(userData, cid, messageID, messageText, timeCreated, isMine, isAudio = '0', isAnnouncement = '0'){
    const messageTime = getTimeFromTimestamp(timeCreated);
    let shortedNick = `${userData['nickname'][0]}${userData['nickname'][userData['nickname'].length - 1]}`;
    let imageComponent = `<p>${shortedNick}</p>`;
    // if (userData.hasOwnProperty('avatar') && userData['avatar']){
    //     imageComponent = `<img alt="${shortedNick}" onerror="handleImgError(this);" src="${configData["CHAT_SERVER_URL_BASE"]}/files/avatar/${userData['_id']}" loading="lazy">`
    // }
    const messageClass = isAnnouncement === '1'?'announcement':isMine?'in':'out';
    const messageOrientation = isMine?'right': 'left';
    let minificationEnabled = currentUser?.preferences?.minify_messages === '1' || await getCurrentSkin(cid) === CONVERSATION_SKINS.PROMPTS;
    let templateSuffix = minificationEnabled? '_minified': '';
    const templateName = isAudio === '1'?`user_message_audio${templateSuffix}`: `user_message${templateSuffix}`;
    if (isAudio === '0') {
        messageText = messageText.replaceAll( '\n', '<br>' );
    }
    let statusIconHTML = '';
    let userTooltip = userData['nickname'];
    if (userData?.is_bot === '1'){
        statusIconHTML = ' <span class="fa fa-robot"></span>'
        userTooltip = `bot ${userTooltip}`
    }
    return await buildHTMLFromTemplate(templateName,
        {'message_class': messageClass,
            'is_announcement': isAnnouncement,
            'image_component': imageComponent,
            'message_id':messageID,
            'user_tooltip': userTooltip,
            'nickname': userData['nickname'],
            'nickname_shrunk': shrinkToFit(userData['nickname'], 15, '..'),
            'status_icon': statusIconHTML,
            'message_text':messageText,
            'message_orientation': messageOrientation,
            'audio_url': `${configData["CHAT_SERVER_URL_BASE"]}/files/audio/${messageID}`,
            'message_time': messageTime});
}

/**
 *
 * @param nick: nickname to shorten
 * @return {string} - shortened nickname
 */
const shrinkNickname = (nick) => {
    const index = nick.indexOf('_');
    return (index !== -1 && index < 7) ? nick.substring(0, index) : nick.substring(0, 7);
}

/**
 * Generates dark color based on username
 * @param username
 * @returns {string} - generated color in hsl format
 */

function generateDarkColorFromUsername(username) {
    if (!username) {
        return 'hsl(270, 70%, 30%)';
    }
    let hash = 0;
    for (let i = 0; i < username.length; i++) {
        hash = username.charCodeAt(i) + ((hash << 5) - hash);
    }
    return `hsl(${hash % 360}, 70%, 30%)`;
}

/**
 * Builds Prompt Skin HTML for submind responses
 * @param promptID: target prompt id
 * @param submindID: user id of submind
 * @param submindUserData: user data of submind
 * @param submindResponse: Responding data of submind to incoming prompt
 * @param submindOpinion: Discussion data of submind to incoming prompt
 * @param submindVote: Vote data of submind in prompt
 * @return {Promise<string|void>} - Submind Data HTML populated with provided data
 */
async function buildSubmindHTML(promptID, submindID, submindUserData, submindResponse, submindOpinion, submindVote) {
    const userNickname = submindUserData['nickname'];
    const participantIcon = await buildPromptParticipantIcon(userNickname);
    const phaseDataObjectMapping = {
        'response': submindResponse,
        'opinion': submindOpinion,
        'vote': submindVote
    }
    let templateData = {
            'prompt_id': promptID,
            'user_id': submindID,
            'user_first_name': submindUserData['first_name'],
            'user_last_name': submindUserData['last_name'],
            'user_nickname': userNickname,
            'participant_icon': participantIcon,
            // 'user_avatar': `${configData["CHAT_SERVER_URL_BASE"]}/files/avatar/${submindID}`,
    }
    const submindPromptData = {}
    for (const [k,v] of Object.entries(phaseDataObjectMapping)){
        submindPromptData[k] = v.message_text
        submindPromptData[`${k}_message_id`] = v?.message_id
        const dateCreated = getTimeFromTimestamp(v?.created_on);
        submindPromptData[`${k}_created_on`] = v?.created_on;
        submindPromptData[`${k}_created_on_tooltip`] = dateCreated? `shouted on: ${dateCreated}`: `no ${k} from ${userNickname} in this prompt`;
    }
    return await buildHTMLFromTemplate("prompt_participant", Object.assign(templateData, submindPromptData));
}


/**
 * Gets winner field HTML based on provided winner
 * @return {string} built winner field HTML
 * @param nickname of the winner
 * @param winner_response
 */
async function buildPromptWinnerHTML(nickname, winner_response) {
    return `
    <div class="d-flex flex-column align-items-center justify-content-center">
        <span class="mt-2 mb-3 font-weight-bold">Selected winner</span>
        ${await buildPromptParticipantIcon(nickname)}
        <div style="max-width: 400px; margin-top: 20px;">
            ${winner_response}
        </div>
    </div>
    `
}

/**
 * Builds prompt participant icon HTML
 * @param nickname of the participant
 * @returns prompt participant icon HTML
 */
async function buildPromptParticipantIcon(nickname) {
    const backgroundColor = generateDarkColorFromUsername(nickname);
    const userNicknameShrunk = shrinkNickname(nickname);
    let tooltip = nickname;
    /* if (submindUserData['is_bot'])  assuming only bots participate for now*/ tooltip = `bot ${tooltip}`;
    const template_data = {
        'user_nickname': nickname,
        'user_nickname_shrunk': userNicknameShrunk,
        'background_color': backgroundColor,
        // 'user_avatar': submindUserData['user_avatar'], not used for now
        'tooltip': tooltip
    }
    return await buildHTMLFromTemplate("prompt_participant_icon", template_data)
}


/**
 * Builds prompt HTML from received prompt data
 * @param prompt: prompt object
 * @return Prompt HTML
 */
async function buildPromptHTML(prompt) {
    let submindsHTML = "";
    let winnerFound = false;
    const promptData = prompt['data'];
    if (prompt['is_completed'] === '0'){
        promptData['winner'] = `Prompt in progress
        <div class="spinner-border spinner-border-sm text-dark" role="status">
            <span class="sr-only">Loading...</span>
        </div>`
    }
    const emptyAnswer = `<h4>-</h4>`;
    for (const submindID of Array.from(setDefault(promptData, 'participating_subminds', []))) {
        let submindUserData;
        try {
            const searchedKeys = ['proposed_responses', 'submind_opinions', 'votes'];
            let isLegacy = false;
            try {
                submindUserData = prompt['user_mapping'][submindID][0];
            } catch (e) {
                console.warn('Detected legacy prompt structure');
                submindUserData = {
                    'nickname': submindID,
                    'first_name': 'Klat',
                    'last_name': 'User',
                    'is_bot': '0'
                }
                isLegacy = true
            }
            const data = {}
            searchedKeys.forEach(key=>{
                try {
                    const messageId = promptData[key][submindID];
                    let value = null;
                    if (!isLegacy) {
                        value = prompt['message_mapping'][messageId][0];
                        value['message_id'] = messageId;
                    }
                    if (!value) {
                        value = {'message_text': emptyAnswer}
                    }
                    data[key] = value;
                }catch (e) {
                    data[key] = {'message_text': emptyAnswer};
                }
            });
            if (promptData['winner'] === submindUserData['nickname']) {
                winnerFound = true;
                promptData['winner'] = await buildPromptWinnerHTML(
                    submindUserData['nickname'],
                    data.proposed_responses['message_text']
                );
            }
            submindsHTML += await buildSubmindHTML(prompt['_id'], submindID, submindUserData,
                                                   data.proposed_responses, data.submind_opinions, data.votes);
        }catch (e) {
            console.log(`Malformed data for ${submindID} (prompt_id=${prompt['_id']}) ex=${e}`);
        }
    }
    if (!winnerFound && prompt['is_completed'] === '1'){
        promptData['winner'] = 'Consensus not reached.'
    }
    return await buildHTMLFromTemplate("prompt_table",
        {'prompt_text': promptData['prompt_text'],
            'selected_winner': promptData['winner'],
            'prompt_participants_data': submindsHTML,
            'prompt_id':prompt['_id'],
            'cid': prompt['cid'],
            'message_time': prompt['created_on']});
}

/**
 * Gets user message HTML from received message data object
 * @param message: Message Object received
 * @param skin: conversation skin
 * @return {Promise<string>} HTML by the provided message data
 */
async function messageHTMLFromData(message, skin=CONVERSATION_SKINS.BASE){
    if (skin === CONVERSATION_SKINS.PROMPTS && message['message_type'] === 'prompt'){
        return buildPromptHTML(message);
    }else{
        const isMine = currentUser && message['user_nickname'] === currentUser['nickname'];
        return buildUserMessageHTML({
                'avatar': message['user_avatar'],
                'nickname': message['user_nickname'],
                'is_bot': message['user_is_bot'],
                '_id': message['user_id']
            },
            message['cid'],
            message['message_id'],
            message['message_text'],
            message['created_on'],
            isMine,
            message?.is_audio,
            message?.is_announcement);
    }
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
 * @param skin: conversation skin to build
 * @returns {string} conversation HTML based on provided data
 */
async function buildConversationHTML(conversationData = {}, skin = CONVERSATION_SKINS.BASE){
    const cid = conversationData['_id'];
    const conversation_name = conversationData['conversation_name'];
    let chatFlowHTML = "";
    if(conversationData.hasOwnProperty('chat_flow')) {
        for (const message of Array.from(conversationData['chat_flow'])) {
            message['cid'] = cid;
            chatFlowHTML += await messageHTMLFromData(message, skin);
            // if (skin === CONVERSATION_SKINS.BASE) {
            // }
        }
    }else{
        chatFlowHTML+=`<div class="blank_chat">No messages in this chat yet...</div>`;
    }
    const conversationNameShrunk = shrinkToFit(conversation_name, 6);
    let nanoHeaderHTML = '';
    if (configData.client === CLIENTS.NANO){
        nanoHeaderHTML = await buildHTMLFromTemplate('nano_header', {'cid': cid})
    }
    return await buildHTMLFromTemplate('conversation',
        {'cid': cid,
         'nano_header': nanoHeaderHTML,
         'conversation_name':conversation_name,
         'conversation_name_shrunk': conversationNameShrunk,
         'chat_flow': chatFlowHTML}, `skin=${skin}`);
}

/**
 * Builds suggestion HTML
 * @param cid: target conversation id
 * @param name: target conversation name
 * @return {Promise<string|void>} HTML with fetched data
 */
const buildSuggestionHTML = async (cid, name) => {
    return await buildHTMLFromTemplate('suggestion', {'cid': cid, 'conversation_name': name})
};
