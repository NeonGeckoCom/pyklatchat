const messageContextMenu = document.getElementById("messageContextMenu")
const messageContextMenuUpvote = document.getElementById('messageContextMenuUpvote');
const messageContextMenuDownvote = document.getElementById('messageContextMenuDownvote');

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
 * @param skin: target conversation skin to consider
 * @return {HTMLElement} ID of the message
 */
const getMessageNode = (messageContainer, skin) => {
    if (skin === CONVERSATION_SKINS.PROMPTS){
        return messageContainer.getElementsByTagName('table')[0];
    }else {
        return messageContainer.getElementsByClassName('chat-body')[0].getElementsByClassName('chat-message')[0];
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
 * Gets list of the next n-older messages
 * @param cid: target conversation id
 * @param skin: target conversation skin
 * @param numMessages: number of messages to add
 */
function addOldMessages(cid, skin=CONVERSATION_SKINS.BASE, numMessages = 10){
    const messageContainer = getMessageListContainer(cid);
    if(messageContainer.children.length > 0) {
        const firstMessageItem = messageContainer.children[0];
        const firstMessageID = getMessageNode(firstMessageItem, skin).id;
        getConversationDataByInput(cid, skin, firstMessageID).then(async conversationData => {
            if (messageContainer) {
                const userMessageList = getUserMessages(conversationData);
                userMessageList.sort((a, b) => {
                    a['created_on'] - b['created_on'];
                }).reverse();
                for (const message of userMessageList) {
                    const messageHTML = await messageHTMLFromData(message, skin);
                    messageContainer.insertAdjacentHTML('afterbegin', messageHTML);
                }
                initMessages(conversationData, skin);
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
            addOldMessages(cid, skin);
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
            if(userNickname && configData.client === CLIENTS.MAIN) await showProfileModal(userNickname)
        });
    }
}


/**
 * Inits addProfileDisplay() on each message of provided conversation
 * @param conversationData: target conversation data
 */
function initProfileDisplay(conversationData){
    getUserMessages(conversationData).forEach(message => {
        addProfileDisplay(conversationData['_id'], message['message_id']);
    });
}

/**
 * Sets user vote to the message
 * @param messageID: target message id
 * @param reaction: reaction to emit for desired message
 */
function voteMessage(messageID, reaction){
    let currentMessageReaction = setDefault( currentUser, 'messageReaction', {} );
    let previousVote = null;
    if (Object.keys(currentMessageReaction).includes(messageID)){
        previousVote = currentMessageReaction[messageID];
        delete currentMessageReaction[messageID];
    }else{
        setDefault( currentUser, 'messageReaction', {} )[messageID] = reaction;
    }
    const cancel = previousVote && previousVote === reaction;
    fetchServer(`chat_api/vote_message/${messageID}?reaction=${reaction.toUpperCase()}`, cancel?REQUEST_METHODS.DELETE:REQUEST_METHODS.PUT).then(res=>{
        if (res.ok){
            if (previousVote) {
                let decrementedElement = document.getElementById( previousVote === 'LIKE' ? `${messageID}_likes_count` : `${messageID}_dislikes_count` );
                decrementedElement.value = parseInt(decrementedElement.value) - 1;
            }
            let incrementedElement = document.getElementById(reaction === 'LIKE'?`${messageID}_likes_count`: `${messageID}_dislikes_count`);
            incrementedElement.value = parseInt(incrementedElement.value) + 1;
        }
    })
}

/**
 * Initialise
 * @param conversationData
 */
function initReactions(conversationData){
    getUserMessages(conversationData).forEach(message => {
        message.addEventListener('contextmenu', (e)=>{
            initMessageContextMenu(e);
        });
        const messageLikes = document.getElementById(`${message['message_id']}_likes`);
        const messageLikesCount = document.getElementById(`${message['message_id']}_likes_count`);
        const messageDislikes = document.getElementById(`${message['message_id']}_dislikes`);
        const messageDislikesCount = document.getElementById(`${message['message_id']}_dislikes_count`);
        const userMessageReactions = message?.reactions;
        if(userMessageReactions){
            let likesCounter = 0;
            let dislikesCounter = 0;
            for (const [userID, reaction] of Object.entries(userMessageReactions)) {
                if (['LIKE', 'DISLIKE'].includes(reaction.toUpperCase())) {
                    if (reaction === 'LIKE') {
                        likesCounter++;
                        messageLikes.hidden = false;
                    } else if (reaction === 'DISLIKE') {
                        dislikesCounter++;
                        messageDislikes.hidden = false;
                    }
                    if (userID === currentUser['_id']) {
                        setDefault( currentUser, 'messageReaction', {} )[message['message_id']] = reaction;
                        reaction === 'LIKE'? messageLikes.style.background = 'blue':
                        reaction === 'DISLIKE'? messageDislikes.style.background = 'blue': null;
                    }
                }
            }
            messageLikesCount.value = likesCounter;
            messageDislikesCount.value = likesCounter;
        }
        messageLikes.addEventListener('click', (e)=>{
            voteMessage(message['message_id'], 'LIKE');
        });
        messageDislikes.addEventListener('click', (e)=>{
            voteMessage(message['message_id'], 'DISLIKE');
        });
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
   if (skin === CONVERSATION_SKINS.BASE) {
       initProfileDisplay(conversationData);
       attachReplies(conversationData);
       addAttachments(conversationData);
       addCommunicationChannelTransformCallback(conversationData);
       initReactions(conversationData);
   }
   // common logic
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

/**
 * Hides Message Context Menu
 */
function hideMessageContextMenu() {
    messageContextMenu.style.display = "none"
}

/**
 * Initializes message context menu based on the fired event
 * @param e {Event} event fired
 */
function initMessageContextMenu(e){
    messageContextMenu.style.display = 'block';
    messageContextMenu.style.left = e.pageX + "px";
    messageContextMenu.style.top = e.pageY + "px";
    const currentMessageId = e.target.id;
    messageContextMenuUpvote.addEventListener('click', (e) => {
        voteMessage(currentMessageId, 'LIKE');
        hideMessageContextMenu();
    });
    messageContextMenuDownvote.addEventListener('click', (e) =>{
        voteMessage(currentMessageId, 'DISLIKE');
        hideMessageContextMenu();
    });
}

document.addEventListener('DOMContentLoaded', (_)=>{
   document.addEventListener('click', (e)=>{
       hideMessageContextMenu();
   }) ;
});
