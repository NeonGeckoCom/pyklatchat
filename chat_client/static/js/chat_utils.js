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
 * @returns {Promise<null|number>}: promise resolving id of added message, -1 if failed to resolve message id creation
 */
async function addMessage(cid, userID=null, messageID=null, messageText, timeCreated, repliedMessageID=null, attachments=[]){
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
            let messageHTML = await buildUserMessageHTML(userData, messageID, messageText, timeCreated, isMine);
            const blankChat = cidList.getElementsByClassName('blank_chat');
            if(blankChat.length>0){
                cidList.removeChild(blankChat[0]);
            }
            cidList.insertAdjacentHTML('beforeend', messageHTML);
            resolveMessageAttachments(messageID, attachments);
            resolveUserReply(messageID, repliedMessageID);
            addConversationParticipant(cid, userData['nickname'], true);
            setParticipantsCount(cid);
            cidList.lastChild.scrollIntoView();
            return messageID;
        }
    }
    return -1;
}

function handleImgError(image) {
    image.parentElement.insertAdjacentHTML('afterbegin',`<p>${image.getAttribute('alt')}</p>`);
    image.parentElement.removeChild(image);
    return true;
}

/**
 * Builds user message HTML
 * @param userData: data of message sender
 * @param messageID: id of user message
 * @param messageText: text of user message
 * @param timeCreated: date of creation
 * @param isMine: if message was emitted by current user
 * @returns {string}: constructed HTML out of input params
 */
async function buildUserMessageHTML(userData, messageID, messageText, timeCreated, isMine){
    const messageTime = getTimeFromTimestamp(timeCreated);
    let imageComponent = "";
    let shortedNick = `${userData['nickname'][0]}${userData['nickname'][userData['nickname'].length - 1]}`;
    if (userData.hasOwnProperty('avatar') && userData['avatar']){
        imageComponent = `<img alt="${shortedNick}" onerror="handleImgError(this);" src="${configData["CHAT_SERVER_URL_BASE"]}/users_api/${userData['_id']}/avatar">`
    }
    if (!imageComponent) {
        imageComponent = `<p>${userData['nickname'][0]}${userData['nickname'][userData['nickname'].length - 1]}</p>`;
    }
    return await buildHTMLFromTemplate('user_message',
        {'is_mine': isMine?"in":"out",
            'image_component': imageComponent,
            'message_id':messageID,
            'nickname': userData['nickname'],
            'message_text':messageText,
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
            repliedText = shrinkToFit(repliedText, 10);
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
 * @param messageID: id of user message
 * @param attachments list of attachments received
 */
function resolveMessageAttachments(messageID,attachments = []){
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
 * Downloads desired content
 * @param content: content to download
 * @param filename: name of the file to download
 * @param contentType: type of the content
 */
function download(content, filename, contentType='application/octet-stream')
{
    if(content) {
        const a = document.createElement('a');
        const blob = new Blob([content], {'type':contentType});
        a.href = window.URL.createObjectURL(blob);
        a.target = 'blank';
        a.download = filename;
        a.click();
        window.URL.revokeObjectURL(content);
    }else{
        console.warn('Skipping downloading as content is invalid')
    }
}

/**
 * Attaches message replies to initialized conversation
 * @param conversationData: conversation data object
 */
function addAttachments(conversationData){
    if(conversationData.hasOwnProperty('chat_flow')) {
        Array.from(conversationData['chat_flow']).forEach(message => {
            resolveMessageAttachments(message['message_id'], message?.attachments);
        });
        Array.from(document.getElementsByClassName('attachment-item')).forEach(attachmentItem=>{
            attachmentItem.addEventListener('click', (e)=>{
               e.preventDefault();
               downloadAttachment(attachmentItem, conversationData['_id'], attachmentItem.parentNode.parentNode.id);
            });
        });
    }
}

/**
 * Extracts filename from path
 * @param path: path to extract from
 */
function getFilenameFromPath(path){
    return path.replace(/.*[\/\\]/, '');
}

/**
 * Converts file to base64
 * @param file: desired file
 * @return {Promise}
 */
const toBase64 = file => new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve(reader.result);
    reader.onerror = error => reject(error);
});


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
 */
async function buildConversation(conversationData={}, remember=true,conversationParentID = 'conversationsBody'){
   if(remember){
       addNewCID(conversationData['_id'], conversationAlignmentKey);
   }
   if(configData.client === CLIENTS.MAIN) {
       conversationParticipants[conversationData['_id']] = {};
   }
   const newConversationHTML = await buildConversationHTML(conversationData);
   const conversationsBody = document.getElementById(conversationParentID);
   conversationsBody.insertAdjacentHTML('afterbegin', newConversationHTML);
   attachReplies(conversationData);
   addAttachments(conversationData);
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
            emitUserMessage(textInputElem, e.target.getAttribute('data-target-cid'),null, attachments);
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
    setTimeout( () => currentConversation.getElementsByClassName('card-body')[0].getElementsByClassName('chat-list')[0].lastElementChild?.scrollIntoView(true), 0);
}

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
 * @returns built template string
 */
async function buildHTMLFromTemplate(templateName, templateContext = {}){
    if(!configData['DISABLE_CACHING'] && loadedComponents.hasOwnProperty(templateName)){
        const html = loadedComponents[templateName];
        return fetchTemplateContext(html, templateContext);
    }else {
        return await fetch(`${configData['CHAT_SERVER_URL_BASE']}/components/${templateName}`)
            .then((response) => {
                if (response.ok) {
                    return response.text();
                }
                throw `template unreachable (HTTP STATUS:${response.status}: ${response.statusText})`
            })
            .then((html) => {
                if (!(configData['DISABLE_CACHING'] || loadedComponents.hasOwnProperty(templateName))) {
                    loadedComponents[templateName] = html;
                }
                return fetchTemplateContext(html, templateContext);
            }).catch(err => console.warn(`Failed to fetch template for ${templateName}: ${err}`));
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
 * @returns {string} conversation HTML based on provided data
 */
async function buildConversationHTML(conversationData = {}){
    const cid = conversationData['_id'];
    const conversation_name = conversationData['conversation_name'];
    let chatFlowHTML = "";
    if(conversationData.hasOwnProperty('chat_flow')) {
        for (const message of Array.from(conversationData['chat_flow'])) {
            const isMine = currentUser && message['user_nickname'] === currentUser['nickname'];
            chatFlowHTML += await buildUserMessageHTML({'avatar':message['user_avatar'],'nickname':message['user_nickname'], '_id': message['user_id']},message['message_id'], message['message_text'], message['created_on'],isMine);
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
 * Gets time object from provided UNIX timestamp
 * @param timestampCreated: UNIX timestamp (in seconds)
 * @returns {string} string time (hours:minutes)
 */
function getTimeFromTimestamp(timestampCreated=0){
    const date = new Date(timestampCreated * 1000);
    const year = date.getFullYear().toString();
    let month = date.getMonth()+1;
    month = month>=10?month.toString():'0'+month.toString();
    let day = date.getDate();

    day = day>=10?day.toString():'0'+day.toString();
    const hours = date.getHours().toString();
    let minutes = date.getMinutes();
    minutes = minutes>=10?minutes.toString():'0'+minutes.toString();
    return strFmtDate(year, month, day, hours, minutes, null);
}

/**
 * Composes date based on input params
 * @param year: desired year
 * @param month: desired month
 * @param day: desired day
 * @param hours: num of hours
 * @param minutes: minutes
 * @param seconds: seconds
 * @return date string
 */
function strFmtDate(year, month, day, hours, minutes, seconds){
    let finalDate = "";
    if(year && month && day){
        finalDate+=`${year}-${month}-${day}`
    }
    if(hours && minutes) {
        finalDate += ` ${hours}:${minutes}`
        if (seconds) {
            finalDate += `:${seconds}`
        }
    }
    return finalDate;
}

/**
 * Emits user message to Socket IO Server
 * @param textInputElem: DOM Element with input text
 * @param cid: Conversation ID
 * @param repliedMessageID: ID of replied message
 * @param attachments: list of attachments file names
 */
function emitUserMessage(textInputElem, cid, repliedMessageID=null, attachments= []){
    if(textInputElem && textInputElem.value){
        const timeCreated = Math.floor(Date.now() / 1000);
        const messageText = textInputElem.value;
        addMessage(cid, currentUser['_id'],null, messageText, timeCreated,repliedMessageID,attachments).then(messageID=>{
            socket.emit('user_message', {'cid':cid,'userID':currentUser['_id'],
                        'messageText':messageText,
                        'messageID':messageID,
                        'attachments': attachments,
                        'timeCreated':timeCreated});
        });
        textInputElem.value = "";
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
 * @param keyName: local storage key to add to
 */
function addNewCID(cid, keyName=conversationAlignmentKey){
    let itemLayout = retrieveItemsLayout(keyName);
    itemLayout.push(cid);
    localStorage.setItem(keyName,JSON.stringify(itemLayout));
}

/**
 * Removed conversation id from local storage
 * @param cid: conversation id to remove
 * @param keyName: local storage key to remove from
 */
function removeCID(cid, keyName=conversationAlignmentKey){
    let itemLayout = retrieveItemsLayout(keyName);
    itemLayout = itemLayout.filter(function(value, index, arr){
        return value !== cid;
    });
    localStorage.setItem(keyName,JSON.stringify(itemLayout));
}

/**
 * Restores chats alignment from the local storage
 *
 * @param keyName: name of the local storage key
**/
function restoreChatAlignment(keyName=conversationAlignmentKey){
    let itemsLayout = retrieveItemsLayout(keyName);
    for (const item of itemsLayout) {
        getConversationDataByInput(item).then(async conversationData=>{
            if(conversationData && Object.keys(conversationData).length > 0) {
                await buildConversation(conversationData, false);
            }else{
                displayAlert(document.getElementById('conversationsBody'),'No matching conversation found','danger');
                removeCID(item);
            }
        });
    }
}

/**
 * Refreshes chat view (e.g. when user session gets updated)
 */
function refreshChatView(){
    Array.from(conversationBody.getElementsByClassName('conversationContainer')).forEach(conversation=>{
       const messages = conversation.getElementsByClassName('card')[0]
           .getElementsByClassName('card-body')[0]
           .getElementsByClassName('chat-list')[0]
           .getElementsByTagName('li');
       Array.from(messages).forEach(message=>{
          if(message.hasAttribute('data-sender')){
              const messageSenderNickname = message.getAttribute('data-sender');
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

document.addEventListener('DOMContentLoaded', (e)=>{
    document.addEventListener('currentUserLoaded',(e)=>{
        restoreChatAlignment();
    });

    if (configData['client'] === CLIENTS.MAIN) {

        addBySearch.addEventListener('click', async (e) => {
            e.preventDefault();
            if (conversationSearchInput.value !== "") {
                getConversationDataByInput(conversationSearchInput.value).then(async conversationData => {
                    if (getOpenedChats().includes(conversationData['_id'])) {
                        displayAlert(document.getElementById('importConversationModalBody'), 'Chat is already displayed', 'danger');
                    } else if (conversationData && Object.keys(conversationData).length > 0) {
                        await buildConversation(conversationData);
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
                    await buildConversation(responseJson);
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
