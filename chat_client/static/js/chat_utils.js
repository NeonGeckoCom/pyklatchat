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
            let messageHTML = buildUserMessageHTML(userData, messageID, messageText, timeCreated, isMine);
            const blankChat = cidList.getElementsByClassName('blank_chat');
            if(blankChat.length>0){
                cidList.removeChild(blankChat[0]);
            }
            cidList.insertAdjacentHTML('beforeend', messageHTML);
            const addedMessage = document.getElementById(messageID);
            resolveMessageAttachments(addedMessage, attachments);
            resolveUserReply(messageID, repliedMessageID);
            addConversationParticipant(cid, userData['nickname'], true);
            setParticipantsCount(cid);
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
 * @returns {string}: constructed HTML out of input params
 */
function buildUserMessageHTML(userData, messageID, messageText, timeCreated, isMine){
    let html = "";
    const messageSideClass = isMine?"in":"out";
    const messageTime = getTimeFromTimestamp(timeCreated);
    const avatarImage = userData.hasOwnProperty('avatar')?userData['avatar']:'default_avatar.png'
    html += `<li class="${messageSideClass}">`
    html += "<div class=\"chat-img\">\n" +
            `   <img alt="Avatar" src="${configData["imageBaseFolder"]+'/'+avatarImage}">\n` +
            "</div>"
    html +=` <div class="chat-body">
                <div class="chat-message" id="${messageID}">
                    <p style="font-size: small;font-weight: bolder;" class="message-nickname">${userData['nickname']}</p>
                    <div class="reply-placeholder mb-2 mt-1"></div>
                    <p class="message-text">${messageText}</p>
                    <br>
                    <small>${messageTime}</small>
                </div>
             </div>`
    html += "</li>"
    return html;
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
    if(messageID && attachments.length > 0){
        const messageElem = document.getElementById(messageID);
        if(messageElem) {
            attachments.forEach(attachment => {
                const attachmentHTML = `<span class="attachment-item">
                                            ${attachment}
                                        </span>`;
                const attachmentPlaceholder = messageElem.getElementsByClassName('attachments-placeholder')[0];
                attachmentPlaceholder.insertAdjacentHTML('afterbegin', attachmentHTML);
            });
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
function addAttachmentDownload(attachmentItem, cid, messageID){
    if(attachmentItem){
        const fileName = attachmentItem.innerText;
        const getFileURL = `${configData['currentURLBase']}/chats/${cid}/${messageID}/${fileName}`;
        fetch(getFileURL).then(response =>
            response.ok?response.formData().then(data => download(data, fileName))
                :console.error(`No file data received for path:${cid}/${messageID}/${fileName}`))
            .catch(err=>console.error(`Failed to fetch: ${getFileURL}: ${err}`));
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
    const a = document.createElement('a');
    const blob = new Blob([content], {'type':contentType});
    a.href = window.URL.createObjectURL(blob);
    a.target = 'blank';
    a.download = filename;
    a.click();
    setTimeout(()=>document.removeChild(a), 0);
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
            addAttachmentDownload(attachmentItem, conversationData['_id'], attachmentItem.parentNode.parentNode.id);
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
 * @param remember: to store this conversation into localStorage (defaults to true)
 */
function buildConversation(conversationData={},remember=true){
   if(remember){
       addNewCID(conversationData['_id'], conversationAlignmentKey);
   }
   conversationParticipants[conversationData['_id']] = {};
   const newConversationHTML = buildConversationHTML(conversationData);
   const conversationsBody = document.getElementById('conversationsBody');
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
        chatInputButton.addEventListener('click', (e)=>{
            const textInputElem = document.getElementById(conversationData['_id']+'-input');
            const attachmentMapping = {};
            let i = 0;
            Array.from(filenamesContainer.getElementsByClassName('filename')).forEach(async filename=>{
                attachmentMapping[filename.innerText] = await toBase64(attachmentsButton.files[i]);
            });
            emitUserMessage(textInputElem, e.target.getAttribute('data-target-cid'), attachmentMapping);
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
        filenamesContainer.style.display = "";
        filenamesContainer.insertAdjacentHTML('afterbegin',
                                                `<span class='filename'>${fileName}</span>`);
        if (filenamesContainer.children.length === configData['maxNumAttachments']) {
            attachmentsButton.disabled = true;
        }
    });
    setParticipantsCount(conversationData['_id']);
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
 * @returns {string} conversation HTML based on provided data (without replies)
 */
function buildConversationHTML(conversationData = {}){
    let html = `<div class="conversationContainer col-xl-6 col-lg-6 col-md-6 col-sm-12 col-12 m-2">
                <div class="card" id="${ conversationData['_id'] }">
                    <div class="card-header">${ conversationData['conversation_name'] }
                        <span class="ml-3" id="participants-list-${conversationData['_id']}">
                            <i class="icon-user" aria-hidden="true"></i> <span id="participants-count-${conversationData['_id']}">0</span>
                        </span>
                        <button type="button" id="close-${conversationData['_id']}" data-target-cid="${conversationData['_id']}" class="close-cid">
                            <span aria-hidden="true">×</span>
                        </button>
                    </div>
                    <div class="card-body height3" style="overflow-y: auto; height: 450px!important;">
                        <ul class="chat-list">`
    if(conversationData.hasOwnProperty('chat_flow')) {
        Array.from(conversationData['chat_flow']).forEach(message => {
            const isMine = currentUser && message['user_nickname'] === currentUser['nickname'];
            html += buildUserMessageHTML({'avatar':message['user_avatar'],'nickname':message['user_nickname']},message['message_id'], message['message_text'], message['created_on'],isMine);
            addConversationParticipant(conversationData['_id'], message['user_nickname']);
        });
    }else{
        html+=`<div class="blank_chat">No messages in this chat yet...</div>`;
    }
    html += `</ul>
             </div>
                   <div class="card-footer">
                        <input class="user_input form-control" id="${conversationData['_id']}-input" type="text" placeholder='Write a Message to "${conversationData['conversation_name']}"'>
                        <button class="send_user_input mt-2 btn btn-success" id="${conversationData['_id']}-send" data-target-cid="${conversationData['_id']}">Send Message</button>
                        <label for="file-input-${conversationData['_id']}" class="attachment-label">
                          <i class="icon-paperclip icon-large" aria-hidden="true"></i>
                        </label>
                        <input type="file" class="file-input fa fa-paperclip" data-target-cid="${conversationData['_id']}" style="display: none;" name="file-input" id="file-input-${conversationData['_id']}" multiple>
                        <div class="filename-container" id="filename-container-${conversationData['_id']}" style="display: none"></div>
                    </div>
                </div>
            </div>`
    return html;
}


/**
 * Gets conversation data based on input string
 * @param input: input string text
 * @returns {Promise<{}>} promise resolving conversation data returned
 */
async function getConversationDataByInput(input=""){
    let conversationData = {};
    if(input && typeof input === "string"){
        const query_url = `${configData['currentURLBase']}/chats/search/${input}`
        await fetch(query_url)
            .then(response => response.ok?response.json():null)
            .then(data => {
                conversationData = data;
            });
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
    let month = date.getMonth();
    month = month>=10?month:'0'+month;
    let day = date.getDay();
    day = day>=10?day:'0'+day;
    const hours = date.getHours();
    let minutes = date.getMinutes();
    minutes = minutes>=10?minutes:'0'+minutes;
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
 * @param attachmentMapping: name to data mapping of attachments to add
 */
function emitUserMessage(textInputElem, cid, repliedMessageID=null, attachmentMapping= {}){
    if(textInputElem && textInputElem.value){
        const timeCreated = Math.floor(Date.now() / 1000);
        const messageText = textInputElem.value;
        addMessage(cid, currentUser['_id'],null, messageText, timeCreated,repliedMessageID,Object.keys(attachmentMapping)).then(messageID=>{
            socket.emit('user_message', {'cid':cid,'userID':currentUser['_id'],
                              'messageText':messageText,
                              'messageID':messageID,
                              'attachments': attachmentMapping,
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
        getConversationDataByInput(item).then(conversationData=>{
            if(conversationData) {
                buildConversation(conversationData, false);
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

document.addEventListener('DOMContentLoaded', (e)=>{
    document.addEventListener('currentUserLoaded',(e)=>{
        restoreChatAlignment();
    });

    addBySearch.addEventListener('click', async (e)=>{
       e.preventDefault();
       if(conversationSearchInput.value!==""){
            getConversationDataByInput(conversationSearchInput.value).then(conversationData=>{
                if(conversationData) {
                    buildConversation(conversationData);
                }else{
                    displayAlert(document.getElementById('importConversationModalBody'),'Cannot find conversation matching your search','danger');
                }
                conversationSearchInput.value = "";
            });
       }
    });

    addNewConversation.addEventListener('click', (e)=>{
       e.preventDefault();
       const newConversationID = document.getElementById('conversationID');
       const newConversationName = document.getElementById('conversationName');
       const isPrivate = document.getElementById('isPrivate');

       let formData = new FormData();

       formData.append('conversation_name', newConversationName.value);
       formData.append('conversation_id', newConversationID?newConversationID.value:null);
       formData.append('is_private', isPrivate.checked)


       fetch(`${configData['currentURLBase']}/chats/new`, {method: 'post', body: formData}).then( async response=>{
                const responseJson = await response.json();
                if(response.ok){
                    buildConversation(responseJson);
                }else{
                    displayAlert(document.getElementById('newConversationModalBody'),'Cannot add new conversation: '+ responseJson['detail'][0]['msg'],'danger');
                }
                newConversationName.value="";
                newConversationID.value = "";
                isPrivate.checked = false;
            });
    });
});
