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
 * Gets message id from the message container DOM element
 * @param messageContainer: DOM Message Container element to consider
 * @return {string} ID of the message
 */
const getMessageId = (messageContainer) => {
    return messageContainer.getElementsByClassName('chat-body')[0].getElementsByClassName('chat-message')[0].id;
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
        let messageHTML = await buildUserMessageHTML(userData, messageID, messageText, timeCreated, isMine, isAudio, isAnnouncement);
        const blankChat = messageList.getElementsByClassName('blank_chat');
        if(blankChat.length>0){
            messageList.removeChild(blankChat[0]);
        }
        messageList.insertAdjacentHTML('beforeend', messageHTML);
        resolveMessageAttachments(cid, messageID, attachments);
        resolveUserReply(messageID, repliedMessageID);
        addProfileDisplay(cid, messageID);
        addConversationParticipant(cid, userData['nickname'], true);
        scrollOnNewMessage(messageList);
        return messageID;
    }
}

/**
 * Gets list of the next n-older messages
 * @param cid: target conversation id
 * @param numMessages: number of messages to add
 */
function addOldMessages(cid, numMessages = 10){
    const messageContainer = getMessageListContainer(cid);
    if(messageContainer.children.length > 0) {
        const firstMessageItem = messageContainer.children[0];
        const firstMessageID = getMessageId(firstMessageItem);
        getConversationDataByInput(cid, firstMessageID).then(async conversationData => {
            if (messageContainer) {
                const userMessageList = getUserMessages(conversationData);
                userMessageList.sort((a, b) => {
                    a['created_on'] - b['created_on'];
                }).reverse();
                for (const message of userMessageList) {
                    const messageHTML = await messageHTMLFromData(message);
                    messageContainer.insertAdjacentHTML('afterbegin', messageHTML);
                }
                initMessages(conversationData);
            }
        }).then(_=>{
            firstMessageItem.scrollIntoView({behavior: "smooth"});
        });
    }
}

/**
 * Array of user messages in given conversation
 * @param conversationData: Conversation Data object to fetch
 */
const getUserMessages = (conversationData) => {
    try {
        return Array.from(conversationData['chat_flow']);
    } catch{
        return [];
    }
}

/**
 * Initializes listener for loading old message on scrolling conversation box
 * @param conversationData: Conversation Data object to fetch
 */
function initLoadOldMessages(conversationData) {
    const cid = conversationData['_id'];
    const messageList = getMessageListContainer(cid);
    const messageListParent = messageList.parentElement;
    setDefault(conversationState[cid],'lastScrollY', 0);
    messageListParent.addEventListener("scroll", async (e) => {
        const oldScrollPosition = conversationState[cid]['scrollY'];
        conversationState[cid]['scrollY'] = e.target.scrollTop;
        if (oldScrollPosition > conversationState[cid]['scrollY'] &&
            !conversationState[cid]['all_messages_displayed'] &&
            conversationState[cid]['scrollY'] === 0) {
            setChatState(cid, 'updating', 'Loading messages...')
            addOldMessages(cid);
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
 * Adds callback for showing profile information on profile avatar click
 * @param cid: target conversation id
 * @param messageId: target message id
 */
function addProfileDisplay(cid, messageId){
    const messageAvatar = document.getElementById(`${messageId}_avatar`);
    if (messageAvatar){
        messageAvatar.addEventListener('click', async (e)=>{
            const userNickname = messageAvatar.getAttribute('data-target');
            if(userNickname) await showProfileModal(userNickname);
        });
    }
}


/**
 * Inits addProfileDisplay() on each message of provided conversation
 * @param conversationData: target conversation data
 */
function initProfileDisplay(conversationData){
    if(conversationData.hasOwnProperty('chat_flow')) {
        getUserMessages(conversationData).forEach(message => {
            addProfileDisplay(conversationData['_id'], message['message_id']);
        });
    }
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
 */
function initMessages(conversationData){
   initProfileDisplay(conversationData);
   attachReplies(conversationData);
   addAttachments(conversationData);
   initLoadOldMessages(conversationData);
   addCommunicationChannelTransformCallback(conversationData);
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
        const timeCreated = Math.floor(Date.now() / 1000);
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
