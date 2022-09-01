const conversationSearchInput = document.getElementById('conversationSearchInput');
const addBySearch = document.getElementById('addBySearch');
const addNewConversation = document.getElementById('addNewConversation');
const conversationBody = document.getElementById('conversationsBody');

let conversationParticipants = {};

/**
 * Adds new conversation participant
 * @param cid: conversation id
 * @param nickname: nickname to add
 * @param updateCount: to update participants count
 */
const addConversationParticipant = (cid, nickname, updateCount = false) => {
    if(!conversationParticipants.hasOwnProperty(cid)){
        conversationParticipants[cid] = {};
    }
    if(!conversationParticipants[cid].hasOwnProperty(nickname)){
        conversationParticipants[cid][nickname] = 1;
    }else{
        conversationParticipants[cid][nickname]++;
    }
    if(updateCount){
        setParticipantsCount(cid);
    }
}

/**
 * Sets participants count for conversation view
 * @param cid: desired conversation id
 */
const setParticipantsCount = (cid) => {
    const participantsCountNode = document.getElementById(`participants-count-${cid}`);
    participantsCountNode.innerText = Object.keys(conversationParticipants[cid]).length;
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
async function addMessage(cid, userID=null, messageID=null, messageText, timeCreated, repliedMessageID=null, attachments=[], isAudio='0', isAnnouncement='0'){
    const cidElem = document.getElementById(cid);
    if(cidElem){
        const cidList = cidElem.getElementsByClassName('card-body')[0].getElementsByClassName('chat-list')[0]
        if(cidList){
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
            const blankChat = cidList.getElementsByClassName('blank_chat');
            if(blankChat.length>0){
                cidList.removeChild(blankChat[0]);
            }
            cidList.insertAdjacentHTML('beforeend', messageHTML);
            resolveMessageAttachments(cid, messageID, attachments);
            resolveUserReply(messageID, repliedMessageID);
            addConversationParticipant(cid, userData['nickname'], true);
            cidList.lastChild.scrollIntoView();
            return messageID;
        }
    }
    return -1;
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
 * Resolves user reply on message
 * @param replyID: id of user reply
 * @param repliedID id of replied message
 */
function resolveUserReply(replyID,repliedID){
    if(repliedID){
        const repliedElem = document.getElementById(repliedID);
        if(repliedElem) {
            let repliedText = repliedElem.getElementsByClassName('message-text')[0].innerText;
            repliedText = shrinkToFit(repliedText, 15);
            const replyHTML = `<a class="reply-text" data-replied-id="${repliedID}">
                                    ${repliedText}
                                </a>`;
            const replyPlaceholder = document.getElementById(replyID).getElementsByClassName('reply-placeholder')[0];
            replyPlaceholder.insertAdjacentHTML('afterbegin', replyHTML);
            attachReplyHighlighting(replyPlaceholder.getElementsByClassName('reply-text')[0]);
        }
    }
}


/**
 * Resolves attachments to the message
 * @param cid: id of conversation
 * @param messageID: id of user message
 * @param attachments list of attachments received
 */
function resolveMessageAttachments(cid, messageID,attachments = []){
    if(messageID) {
        const messageElem = document.getElementById(messageID);
        if(messageElem) {
            const attachmentToggle = messageElem.getElementsByClassName('attachment-toggle')[0];
            if (attachments.length > 0) {
                if (messageElem) {
                    const attachmentPlaceholder = messageElem.getElementsByClassName('attachments-placeholder')[0];
                    attachments.forEach(attachment => {
                        const attachmentHTML = `<span class="attachment-item" data-file-name="${attachment['name']}" data-mime="${attachment['mime']}" data-size="${attachment['size']}">
                                            ${shrinkToFit(attachment['name'], 10)}
                                        </span><br>`;
                        attachmentPlaceholder.insertAdjacentHTML('afterbegin', attachmentHTML);
                    });
                    attachmentToggle.addEventListener('click', (e) => {
                        attachmentPlaceholder.style.display = attachmentPlaceholder.style.display === "none" ? "" : "none";
                    });
                    activateAttachments(cid, attachmentPlaceholder);
                }
            } else {
                attachmentToggle.style.display = "none";
            }
        }
    }
}

/**
 * Attaches reply highlighting for reply item
 * @param replyItem reply item element
 */
function attachReplyHighlighting(replyItem){
    replyItem.addEventListener('click', (e)=>{
        const repliedItem = document.getElementById(replyItem.getAttribute('data-replied-id'));
        const backgroundParent = repliedItem.parentElement.parentElement;
        repliedItem.scrollIntoView();
        backgroundParent.classList.remove('message-selected');
        setTimeout(() => backgroundParent.classList.add('message-selected'),500);
    });
}

/**
 * Attaches message replies to initialized conversation
 * @param conversationData: conversation data object
 */
function attachReplies(conversationData){
    if(conversationData.hasOwnProperty('chat_flow')) {
        Array.from(conversationData['chat_flow']).forEach(message => {
            resolveUserReply(message['message_id'], message?.replied_message);
        });
        Array.from(document.getElementsByClassName('reply-text')).forEach(replyItem=>{
            attachReplyHighlighting(replyItem);
        });
    }
}

/**
 * Adds download request on attachment item click
 * @param attachmentItem: desired attachment item
 * @param cid: current conversation id
 * @param messageID: current message id
 */
function downloadAttachment(attachmentItem, cid, messageID){
    if(attachmentItem){
        const fileName = attachmentItem.getAttribute('data-file-name');
        const mime = attachmentItem.getAttribute('data-mime');
        const getFileURL = `${configData['CHAT_SERVER_URL_BASE']}/chat_api/${messageID}/get_file/${fileName}`;
        fetch(getFileURL).then(async response => {
            response.ok ?
                download(await response.blob(), fileName, mime)
                :console.error(`No file data received for path, 
                                  cid=${cid};\n
                                  message_id=${messageID};\n
                                  file_name=${fileName}`)
        }).catch(err=>console.error(`Failed to fetch: ${getFileURL}: ${err}`));
    }
}

/**
 * Attaches message replies to initialized conversation
 * @param conversationData: conversation data object
 */
function addAttachments(conversationData){
    if(conversationData.hasOwnProperty('chat_flow')) {
        Array.from(conversationData['chat_flow']).forEach(message => {
            resolveMessageAttachments(conversationData['_id'], message['message_id'], message?.attachments);
        });
    }
}

/**
 * Activates attachments event listeners for message attachments in specified conversation
 * @param cid: desired conversation id
 * @param elem: parent element for attachment (defaults to document)
 */
function activateAttachments(cid, elem=null){
    if (!elem){
        elem = document;
    }
    Array.from(elem.getElementsByClassName('attachment-item')).forEach(attachmentItem=>{
        attachmentItem.addEventListener('click', (e)=>{
           e.preventDefault();
           downloadAttachment(attachmentItem, cid, attachmentItem.parentNode.parentNode.id);
        });
    });
}


let __inputFileList = {};

/**
 * Gets uploaded files from specified conversation id
 * @param cid specified conversation id
 * @return {*} list of files from specified cid if any
 */
function getUploadedFiles(cid){
    if(__inputFileList.hasOwnProperty(cid)){
        return __inputFileList[cid];
    }return [];
}

/**
 * Cleans uploaded files per conversation
 */
function cleanUploadedFiles(cid){
    if(__inputFileList.hasOwnProperty(cid)) {
        delete __inputFileList[cid];
    }
    const attachmentsButton = document.getElementById('file-input-'+cid);
    attachmentsButton.value = "";
    const fileContainer = document.getElementById('filename-container-'+cid);
    fileContainer.innerHTML = "";
}

/**
 * Adds File upload to specified cid
 * @param cid: mentioned cid
 * @param file: File object
 */
function addUpload(cid, file){
    if(!__inputFileList.hasOwnProperty(cid)){
        __inputFileList[cid] = [];
    }
    __inputFileList[cid].push(file);
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
        Array.from(conversationData['chat_flow']).forEach(message => {
            addMessageTransformCallback(conversationData['_id'], message['message_id'], message?.is_audio);
        });
    }
}

/**
 * Adds event listener for audio recording
 * @param conversationData: conversation data object
 */
async function addRecorder(conversationData) {

    const cid = conversationData["_id"];

    const recorderButton = document.getElementById(`${cid}-audio-input`);

    const recorder = await recordAudio(cid);

    recorderButton.onmousedown = function () {
        recorder.start();
    };

    recorderButton.onmouseup = async function () {
        recorder.stop().then(audio=>{
            const audioBlob = toBase64(audio['audioBlob']);
            console.log('audioBlob=',audioBlob);
            return audioBlob;
        }).then(encodedAudio=>emitUserMessage(encodedAudio, conversationData['_id'], null, [], '1', '0'));
    };
}

/**
 * Builds new conversation HTML from provided data and attaches it to the list of displayed conversations
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
 * @param conversationParentID: ID of conversation parent
 * @param remember: to store this conversation into localStorage (defaults to true)
 *
 * @return id of the built conversation
 */
async function buildConversation(conversationData={}, remember=true,conversationParentID = 'conversationsBody'){
   if(remember){
       addNewCID(conversationData['_id']);
   }
   if(configData.client === CLIENTS.MAIN) {
       conversationParticipants[conversationData['_id']] = {};
   }
   const newConversationHTML = await buildConversationHTML(conversationData);
   const conversationsBody = document.getElementById(conversationParentID);
   conversationsBody.insertAdjacentHTML('afterbegin', newConversationHTML);
   attachReplies(conversationData);
   addAttachments(conversationData);
   addCommunicationChannelTransformCallback(conversationData);
   await addRecorder(conversationData);

   const currentConversation = document.getElementById(conversationData['_id']);
   const conversationParent = currentConversation.parentElement;
   const conversationHolder = conversationParent.parentElement;

   const chatInputButton = document.getElementById(conversationData['_id']+'-send');
   const filenamesContainer = document.getElementById(`filename-container-${conversationData['_id']}`)
   const attachmentsButton = document.getElementById('file-input-'+conversationData['_id']);

    if(chatInputButton.hasAttribute('data-target-cid')) {
        chatInputButton.addEventListener('click', async (e)=>{
            const textInputElem = document.getElementById(conversationData['_id']+'-input');
            let attachments = [];
            const currCid = chatInputButton.getAttribute('data-target-cid');
            const filesArr = getUploadedFiles(currCid);
            if (filesArr.length > 0){
                console.info('Processing attachments array...')
                let errorOccurred = null;
                const formData = new FormData();
                filesArr.forEach(file=>{
                    const generatedFileName = `${generateUUID(10,'00041000')}.${file.name.split('.').pop()}`;
                    attachments.push({'name': generatedFileName, 'size': file.size, 'mime': file.type});
                    const renamedFile = new File([file], generatedFileName, {type: file.type});
                    formData.append('files', renamedFile);
                });
                cleanUploadedFiles(currCid);

                console.log('Received attachments array: ', attachments)
                const query_url = `${configData['CHAT_SERVER_URL_BASE']}/chat_api/${conversationData['_id']}/store_files`;
                await fetch(query_url, {method:'POST',
                                              body:formData})
                    .then(response => response.ok?console.log('File stored successfully'):null).catch(err=>{
                        errorOccurred=err;
                    });
                if(errorOccurred){
                    console.error(`Error during attachments preparation: ${errorOccurred}, skipping message sending`);
                    return
                }
            }
            emitUserMessage(textInputElem, e.target.getAttribute('data-target-cid'),null, attachments, '0', '0');
            textInputElem.value = "";
        });
    }

    const chatCloseButton = document.getElementById(`close-${conversationData['_id']}`);
    if(chatCloseButton.hasAttribute('data-target-cid')) {
        chatCloseButton.addEventListener('click', (e)=>{
            conversationHolder.removeChild(conversationParent);
            removeCID(conversationData['_id']);
        });
    }

    attachmentsButton.addEventListener('change', (e)=>{
        e.preventDefault();
        const fileName = getFilenameFromPath(e.currentTarget.value);
        const lastFile = attachmentsButton.files[attachmentsButton.files.length - 1]
        if(lastFile.size > configData['maxUploadSize']){
            console.warn(`Uploaded file is too big`);
        }else {
            addUpload(attachmentsButton.parentNode.parentNode.id, lastFile);
            filenamesContainer.insertAdjacentHTML('afterbegin',
                `<span class='filename'>${fileName}</span>`);
            filenamesContainer.style.display = "";
            if (filenamesContainer.children.length === configData['maxNumAttachments']) {
                attachmentsButton.disabled = true;
            }
        }
    });
    setParticipantsCount(conversationData['_id']);
    await initLanguageSelector(conversationData['_id']);
    setTimeout(() => currentConversation.getElementsByClassName('card-body')[0].getElementsByClassName('chat-list')[0].lastElementChild?.scrollIntoView(true), 0);
    return conversationData['_id'];
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
            const isMine = currentUser && message['user_nickname'] === currentUser['nickname'];

            chatFlowHTML += await buildUserMessageHTML({'avatar':message['user_avatar'],'nickname':message['user_nickname'], '_id': message['user_id']},message['message_id'], message['message_text'], message['created_on'],isMine,message?.is_audio, message?.is_announcement);
            addConversationParticipant(conversationData['_id'], message['user_nickname']);
        }
    }else{
        chatFlowHTML+=`<div class="blank_chat">No messages in this chat yet...</div>`;
    }
    return await buildHTMLFromTemplate('conversation',
        {'cid': cid, 'conversation_name':conversation_name, 'chat_flow': chatFlowHTML});
}


/**
 * Gets conversation data based on input string
 * @param input: input string text
 * @returns {Promise<{}>} promise resolving conversation data returned
 */
async function getConversationDataByInput(input=""){
    let conversationData = {};
    if(input && typeof input === "string"){
        const query_url = `${configData['CHAT_SERVER_URL_BASE']}/chat_api/search/${input}`
        await fetch(query_url)
            .then(response => {
                if(response.ok){
                    return response.json();
                }else{
                    console.log('here')
                    throw response.statusText;
                }
            })
            .then(data => {
                conversationData = data;
            }).catch(err=> console.warn('Failed to fulfill request due to error:',err));
    }
    return conversationData;
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
        addMessage(cid, currentUser['_id'],null, messageText, timeCreated,repliedMessageID,attachments, isAudio, isAnnouncement).then(messageID=>{
            socket.emit('user_message',
                {'cid':cid,
                 'userID':currentUser['_id'],
                 'messageText':messageText,
                 'messageID':messageID,
                 'attachments': attachments,
                 'isAudio': isAudio,
                 'isAnnouncement': isAnnouncement,
                 'timeCreated':timeCreated
                });
            addMessageTransformCallback(cid, messageID, isAudio);
            // TODO: support for audio message translation
            if(isAudio !== '1'){
                sendLanguageUpdateRequest(cid, messageID);
            }
        });
        if (isAudio === '0'){
            textInputElem.value = "";
        }
    }
}

/**
 * Retrieves conversation layout from local storage
 * @param keyName: key to lookup in local storage (defaults to provided in config.js)
 * @returns {Array} array of conversations from local storage
 */
function retrieveItemsLayout(keyName=conversationAlignmentKey){
    let itemsLayout = localStorage.getItem(keyName);
    if(itemsLayout){
        itemsLayout = JSON.parse(itemsLayout);
    }else{
        itemsLayout = [];
    }
    return itemsLayout;
}

/**
 * Adds new conversation id to local storage
 * @param cid: conversation id to add
 */
function addNewCID(cid){
    const keyName = conversationAlignmentKey;
    let itemLayout = retrieveItemsLayout(keyName);
    itemLayout.push(cid);
    localStorage.setItem(keyName,JSON.stringify(itemLayout));
}

/**
 * Removed conversation id from local storage
 * @param cid: conversation id to remove
 */
function removeCID(cid){
    const keyName = conversationAlignmentKey;
    let itemLayout = retrieveItemsLayout(keyName);
    itemLayout = itemLayout.filter(function(value, index, arr){
        return value !== cid;
    });
    localStorage.setItem(keyName,JSON.stringify(itemLayout));
}

/**
 * Checks if cid is in local storage
 * @param cid
 * @return true if cid is displayed, false otherwise
 */
function isDisplayed(cid){
    return retrieveItemsLayout().includes(cid);
}

/**
 * Custom Event fired on supported languages init
 * @type {CustomEvent<string>}
 */
const chatAlignmentRestoredEvent = new CustomEvent("chatAlignmentRestored", { "detail": "Event that is fired when chat alignment is restored" });

/**
 * Restores chats alignment from the local storage
 *
 * @param keyName: name of the local storage key
**/
async function restoreChatAlignment(keyName=conversationAlignmentKey){
    let itemsLayout = retrieveItemsLayout(keyName);
    for (const item of itemsLayout) {
        await getConversationDataByInput(item).then(async conversationData=>{
            if(conversationData && Object.keys(conversationData).length > 0) {
                await buildConversation(conversationData, false);
            }else{
                displayAlert(document.getElementById('conversationsBody'),'No matching conversation found','danger');
                removeCID(item);
            }
        });
    }
    console.log('Chat Alignment Restored')
    document.dispatchEvent(chatAlignmentRestoredEvent);
}

/**
 * Gets array of messages for provided conversation id
 * @param cid: target conversation id
 * @return array of message DOM objects under given conversation
 */
function getMessagesOfCID(cid){
    let messages = []
    const conversation = document.getElementById(cid);
    if(conversation){
        const listItems =  conversation.getElementsByClassName('card-body')[0]
                                       .getElementsByClassName('chat-list')[0]
                                       .getElementsByTagName('li');
        Array.from(listItems).forEach(li=>{
           if(li.classList.contains('in') || li.classList.contains('out')){
               const messageNode = li.getElementsByClassName('chat-body')[0].getElementsByClassName('chat-message')[0];
               // console.debug(`pushing shout_id=${messageNode.id}`)
               messages.push(messageNode);
           }
        });
    }
    return messages;
}

/**
 * Refreshes chat view (e.g. when user session gets updated)
 */
function refreshChatView(){
    Array.from(conversationBody.getElementsByClassName('conversationContainer')).forEach(async conversation=>{
       const messages = getMessagesOfCID(conversation.id);
       Array.from(messages).forEach(message=>{
          if(message.hasAttribute('data-sender')){
              const messageSenderNickname = message.getAttribute('data-sender');
              console.log(`messageSenderNickname=${messageSenderNickname}`)
              message.className = currentUser && messageSenderNickname === currentUser['nickname']?'in':'out';
          }
       });
    });
}

/**
 * Gets all opened chats
 * @return {[]} list of displayed chat ids
 */
function getOpenedChats(){
    let cids = [];
    Array.from(conversationBody.getElementsByClassName('conversationContainer')).forEach(conversationContainer=>{
        cids.push(conversationContainer.getElementsByClassName('card')[0].id);
    });
    return cids;
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

const CHAT_STATES = ['active', 'updating'];

/**
 * Sets state to the desired cid
 * @param cid: desired conversation id
 * @param state: desired state
 * @param state_msg: message following state transition (e.g. why chat is updating)
 */
function setChatState(cid, state='active', state_msg = ''){

    console.log(`cid=${cid}, state=${state}, state_msg=${state_msg}`)
    if (!CHAT_STATES.includes(state)){
        console.error(`Invalid transition state provided, should be one of ${CHAT_STATES}`);
        return -1;
    }else{
        const cidNode = document.getElementById(cid);
        const spinner = document.getElementById(`${cid}-spinner`);
        const spinnerUpdateMsg = document.getElementById(`${cid}-update-msg`);
        if (state === 'updating'){
            cidNode.classList.add('chat-loading');
            spinner.style.setProperty('display', 'flex', 'important');
            spinnerUpdateMsg.innerHTML = state_msg;
        }else if(state === 'active'){
            cidNode.classList.remove('chat-loading');
            spinner.style.setProperty('display', 'none', 'important');
            spinnerUpdateMsg.innerHTML = '';
        }
    }
}

document.addEventListener('DOMContentLoaded', (e)=>{

    document.addEventListener('supportedLanguagesLoaded', async (e)=>{
        await refreshCurrentUser(false).then(_=>restoreChatAlignment()).then(_=>refreshCurrentUser(true)).then(_=>requestChatsLanguageRefresh());
    });

    if (configData['client'] === CLIENTS.MAIN) {
        addBySearch.addEventListener('click', async (e) => {
            e.preventDefault();
            if (conversationSearchInput.value !== "") {
                getConversationDataByInput(conversationSearchInput.value).then(async conversationData => {
                    if (getOpenedChats().includes(conversationData['_id'])) {
                        displayAlert(document.getElementById('importConversationModalBody'), 'Chat is already displayed', 'danger');
                    } else if (conversationData && Object.keys(conversationData).length > 0) {
                        await buildConversation(conversationData).then(async cid=>{
                            await sendLanguageUpdateRequest(cid);
                        });
                    } else {
                        displayAlert(document.getElementById('importConversationModalBody'), 'Cannot find conversation matching your search', 'danger');
                    }
                    conversationSearchInput.value = "";
                });
            }
        });
        addNewConversation.addEventListener('click', (e) => {
            e.preventDefault();
            const newConversationID = document.getElementById('conversationID');
            const newConversationName = document.getElementById('conversationName');
            const isPrivate = document.getElementById('isPrivate');

            let formData = new FormData();

            formData.append('conversation_name', newConversationName.value);
            formData.append('conversation_id', newConversationID ? newConversationID.value : null);
            formData.append('is_private', isPrivate.checked)


            fetch(`${configData['currentURLBase']}/chats/new`, {
                method: 'post',
                body: formData
            }).then(async response => {
                const responseJson = await response.json();
                if (response.ok) {
                    await buildConversation(responseJson).then(async cid=>{
                        await initLanguageSelector(cid);
                        console.log(`inited language selector for ${cid}`);
                    });
                } else {
                    displayAlert(document.getElementById('newConversationModalBody'), 'Cannot add new conversation: ' + responseJson['detail'][0]['msg'], 'danger');
                }
                newConversationName.value = "";
                newConversationID.value = "";
                isPrivate.checked = false;
            });
        });
    }
});
