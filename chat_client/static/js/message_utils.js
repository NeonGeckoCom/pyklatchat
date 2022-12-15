/**
 * Returns DOM container for message elements under specific conversation id
 * @param cid: conversation id to consider
 * @return {Element} DOM container for message elements of considered conversation
 */
const getMessageListContainer = (cid) => {
    const cidElem = document.getElementById(cid);
    if(cidElem){
        return cidElem.getElementsByClassName('card-body')[0].getElementsByClassName('chat-list')[0]
    }
}

/**
 * Gets message node from the message container
 * @param messageContainer: DOM Message Container element to consider
 * @param validateType: type of message to validate
 * @return {HTMLElement} ID of the message
 */
const getMessageNode = (messageContainer, validateType=null) => {
    let detectedType;
    let node
    if (messageContainer.getElementsByTagName('table').length > 0) {
        detectedType = 'prompt';
        node = messageContainer.getElementsByTagName( 'table' )[0];
    }else{
        detectedType = 'plain'
        node = messageContainer.getElementsByClassName('chat-body')[0].getElementsByClassName('chat-message')[0];
    }
    if (validateType && validateType!==detectedType){
        return null;
    }else{
        return node;
    }
}

/**
 * Adds new message to desired conversation id
 * @param cid: desired conversation id
 * @param userID: message sender id
 * @param messageID: id of sent message (gets generated if null)
 * @param messageText: text of the message
 * @param timeCreated: timestamp for message creation
 * @param repliedMessageID: id of the replied message (optional)
 * @param attachments: array of attachments to add (optional)
 * @param isAudio: is audio message (defaults to '0')
 * @param isAnnouncement: is message an announcement (defaults to "0")
 * @returns {Promise<null|number>}: promise resolving id of added message, -1 if failed to resolve message id creation
 */
async function addNewMessage(cid, userID=null, messageID=null, messageText, timeCreated, repliedMessageID=null, attachments=[], isAudio='0', isAnnouncement='0'){
    const messageList = getMessageListContainer(cid);
    if(messageList){
        let userData;
        const isMine = userID === currentUser['_id'];
        if(isMine) {
            userData = currentUser;
        }else{
            userData = await getUserData(userID);
        }
        if(!messageID) {
            messageID = generateUUID();
        }
        let messageHTML = await buildUserMessageHTML(userData, cid, messageID, messageText, timeCreated, isMine, isAudio, isAnnouncement);
        const blankChat = messageList.getElementsByClassName('blank_chat');
        if(blankChat.length>0){
            messageList.removeChild(blankChat[0]);
        }
        messageList.insertAdjacentHTML('beforeend', messageHTML);
        resolveMessageAttachments(cid, messageID, attachments);
        resolveUserReply(messageID, repliedMessageID);
        addProfileDisplay(cid, messageID, 'plain');
        addConversationParticipant(cid, userData['nickname'], true);
        scrollOnNewMessage(messageList);
        return messageID;
    }
}

const PROMPT_STATES = {
    1: 'RESP',
    2: 'DISC',
    3: 'VOTE'
}

/**
 * Returns HTML Element representing user row in prompt
 * @param promptID: target prompt id
 * @param userID: target user id
 * @return {HTMLElement}: HTML Element containing user prompt data
 */
const getUserPromptTR = (promptID, userID) => {
    return document.getElementById(`${promptID}_${userID}_prompt_row`);
}

/**
 * Adds prompt message of specified user id
 * @param cid: target conversation id
 * @param userID: target submind user id
 * @param messageText: message of submind
 * @param promptId: target prompt id
 * @param promptState: prompt state to consider
 */
async function addPromptMessage(cid, userID, messageText, promptId, promptState){
    const tableBody = document.getElementById(`${promptId}_tbody`);
    if (await getCurrentSkin(cid) === CONVERSATION_SKINS.PROMPTS){
        try {
            promptState = PROMPT_STATES[promptState].toLowerCase();
            if (!getUserPromptTR(promptId, userID)) {
                const userData = await getUserData(userID);
                const newUserRow = await buildSubmindHTML(promptId, userID, userData, '', '', '');
                tableBody.insertAdjacentHTML('beforeend', newUserRow);
            }
            try {
                const messageElem = document.getElementById(`${promptId}_${userID}_${promptState}`);
                messageElem.innerText = messageText;
            } catch (e) {
                console.warn(`Failed to add prompt message (${cid},${userID}, ${messageText}, ${promptId}, ${promptState}) - ${e}`)
            }
        } catch (e) {
            console.info(`Skipping message of invalid prompt state - ${promptState}`);
        }
    }
}


/**
 * Returns first message id based on given element
 * @param firstChild: DOM element of first message child
 */
function getFirstMessageFromCID(firstChild){
    if (firstChild.classList.contains('prompt-item')){
        const promptTable = firstChild.getElementsByTagName('table')[0];
        const promptID = promptTable.id;
        const promptTBody = promptTable.getElementsByTagName('tbody')[0];
        let currentRecentMessage = null;
        let currentOldestTS = null;
        Array.from(promptTBody.getElementsByTagName('tr')).forEach(tr=>{
            const submindID = tr.getAttribute('data-submind-id');
            ['resp', 'opinion', 'vote'].forEach(phase=>{
               const phaseElem = document.getElementById(`${promptID}_${submindID}_${phase}`);
               if (phaseElem){
                   let createdOn = phaseElem.getAttribute(`data-created-on`);
                   const messageID = phaseElem.getAttribute(`data-message-id`)
                   if (createdOn && messageID){
                       createdOn = parseInt(createdOn);
                       if (!currentOldestTS || createdOn < currentOldestTS){
                           currentOldestTS = createdOn;
                           currentRecentMessage = messageID;
                       }
                   }
               }
            });
        });
        return currentRecentMessage;
    }else{
        return getMessageNode(firstChild, 'plain')?.id;
    }
}

/**
 * Gets list of the next n-older messages
 * @param cid: target conversation id
 * @param skin: target conversation skin
 */
async function addOldMessages(cid, skin=CONVERSATION_SKINS.BASE) {
    const messageContainer = getMessageListContainer( cid );
    if (messageContainer.children.length > 0) {
        for (let i = 0; i < messageContainer.children.length; i++) {
            const firstMessageItem = messageContainer.children[i];
            const firstMessageID = getFirstMessageFromCID( firstMessageItem );
            if (firstMessageID) {
                const numMessages = await getCurrentSkin(cid) === CONVERSATION_SKINS.PROMPTS? 50: 20;
                await getConversationDataByInput( cid, skin, firstMessageID, numMessages, null ).then( async conversationData => {
                    if (messageContainer) {
                        const userMessageList = getUserMessages( conversationData, null );
                        userMessageList.sort( (a, b) => {
                            a['created_on'] - b['created_on'];
                        } ).reverse();
                        for (const message of userMessageList) {
                            message['cid'] = cid;
                            if (!isDisplayed( getMessageID( message ) )) {
                                const messageHTML = await messageHTMLFromData( message, skin );
                                messageContainer.insertAdjacentHTML( 'afterbegin', messageHTML );
                            } else {
                                console.debug( `!!message_id=${message["message_id"]} is already displayed` )
                            }
                        }
                        initMessages( conversationData, skin );
                    }
                } ).then( _ => {
                    firstMessageItem.scrollIntoView( {behavior: "smooth"} );
                } );
                break;
            } else {
                console.warn( `NONE first message id detected for cid=${cid}` )
            }
        }
    }
}


/**
 * Returns message id based on message type
 * @param message: message object to check
 * @returns {null|*} message id extracted if valid message type detected
 */
const getMessageID = (message) => {
    switch (message['message_type']){
        case 'plain':
            return message['message_id'];
        case 'prompt':
            return message['_id'];
        default:
            console.warn(`Invalid message structure received - ${message}`);
            return null;
    }
}

/**
 * Array of user messages in given conversation
 * @param conversationData: Conversation Data object to fetch
 * @param forceType: to force particular type of messages among the chat flow
 */
const getUserMessages = (conversationData, forceType='plain') => {
    try {
        let messages = Array.from(conversationData['chat_flow']);
        if (forceType){
            messages = messages.filter(message=> message['message_type'] === forceType);
        }
        return messages;
    } catch{
        return [];
    }
}

/**
 * Initializes listener for loading old message on scrolling conversation box
 * @param conversationData: Conversation Data object to fetch
 * @param skin: conversation skin to apply
 */
function initLoadOldMessages(conversationData, skin) {
    const cid = conversationData['_id'];
    const messageList = getMessageListContainer(cid);
    const messageListParent = messageList.parentElement;
    setDefault(setDefault(conversationState, cid, {}),'lastScrollY', 0);
    messageListParent.addEventListener("scroll", async (e) => {
        const oldScrollPosition = conversationState[cid]['scrollY'];
        conversationState[cid]['scrollY'] = e.target.scrollTop;
        if (oldScrollPosition > conversationState[cid]['scrollY'] &&
            !conversationState[cid]['all_messages_displayed'] &&
            conversationState[cid]['scrollY'] === 0) {
            setChatState(cid, 'updating', 'Loading messages...')
            await addOldMessages(cid, skin);
            for(const inputType of ['incoming', 'outcoming']){
                await requestTranslation(cid, null, null, inputType);
            }
            setTimeout( () => {
                setChatState(cid, 'active');
            }, 700);
        }
    });
}

/**
 * Attaches event listener to display element's target user profile
 * @param elem: target DOM element
 */
function attachTargetProfileDisplay(elem){
    if (elem) {
        elem.addEventListener( 'click', async (_) => {
            const userNickname = elem.getAttribute( 'data-target' );
            if (userNickname) await showProfileModal( userNickname )
        } );
    }
}

/**
 * Adds callback for showing profile information on profile avatar click
 * @param cid: target conversation id
 * @param messageId: target message id
 * @param messageType: type of message to display
 */
function addProfileDisplay(cid, messageId, messageType='plain'){
    if (messageType === 'plain') {
        attachTargetProfileDisplay(document.getElementById( `${messageId}_avatar` ))
    }else if (messageType === 'prompt'){
        const promptTBody = document.getElementById(`${messageId}_tbody`);
        const rows = promptTBody.getElementsByTagName('tr');
        Array.from(rows).forEach(row=>{
            attachTargetProfileDisplay(Array.from(row.getElementsByTagName('td'))[0].getElementsByClassName('chat-img')[0]);
        })
    }
}


/**
 * Inits addProfileDisplay() on each message of provided conversation
 * @param conversationData: target conversation data
 */
function initProfileDisplay(conversationData){
    getUserMessages(conversationData, null).forEach(message => {
        addProfileDisplay( conversationData['_id'], getMessageID(message), message['message_type']);
    });
}


/**
 * Initializes messages based on provided conversation aata
 * @param conversationData: JS Object containing conversation data of type:
 * {
 *     '_id': 'id of conversation',
 *     'conversation_name': 'title of the conversation',
 *     'chat_flow': [{
 *         'user_nickname': 'nickname of sender',
 *         'user_avatar': 'avatar of sender',
 *         'message_id': 'id of the message',
 *         'message_text': 'text of the message',
 *         'is_audio': true if message is an audio message
 *         'is_announcement': true if message is considered to be an announcement
 *         'created_on': 'creation time of the message'
 *     }, ... (num of user messages returned)]
 * }
 * @param skin: target conversation skin to consider
 */
function initMessages(conversationData, skin = CONVERSATION_SKINS.BASE){
    initProfileDisplay(conversationData);
    attachReplies(conversationData);
    addAttachments(conversationData);
    addCommunicationChannelTransformCallback(conversationData);
    initLoadOldMessages(conversationData, skin);
}

/**
 * Emits user message to Socket IO Server
 * @param textInputElem: DOM Element with input text (audio object if isAudio=true)
 * @param cid: Conversation ID
 * @param repliedMessageID: ID of replied message
 * @param attachments: list of attachments file names
 * @param isAudio: is audio message being emitted (defaults to '0')
 * @param isAnnouncement: is message an announcement (defaults to '0')
 */
function emitUserMessage(textInputElem, cid, repliedMessageID=null, attachments= [], isAudio='0', isAnnouncement='0'){
    if(isAudio === '1' || textInputElem && textInputElem.value){
        const timeCreated = getCurrentTimestamp();
        let messageText;
        if (isAudio === '1'){
            messageText = textInputElem;
        }else {
            messageText = textInputElem.value;
        }
        addNewMessage(cid, currentUser['_id'],null, messageText, timeCreated,repliedMessageID,attachments, isAudio, isAnnouncement).then(async messageID=>{
            const preferredShoutLang = getPreferredLanguage(cid, 'outcoming');
            socket.emitAuthorized('user_message',
                {'cid':cid,
                 'userID':currentUser['_id'],
                 'messageText':messageText,
                 'messageID':messageID,
                 'lang': preferredShoutLang,
                 'attachments': attachments,
                 'isAudio': isAudio,
                 'isAnnouncement': isAnnouncement,
                 'timeCreated':timeCreated
                });
            if(preferredShoutLang !== 'en'){
                await requestTranslation(cid, messageID, 'en', 'outcoming', true);
            }
            addMessageTransformCallback(cid, messageID, isAudio);
        });
        if (isAudio === '0'){
            textInputElem.value = "";
        }
    }
}
