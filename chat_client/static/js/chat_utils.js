const conversationSearchInput = document.getElementById('conversationSearchInput');
const addBySearch = document.getElementById('addBySearch');
const addNewConversation = document.getElementById('addNewConversation');
const conversationBody = document.getElementById('conversationsBody');

async function addMessage(cid, userID=null, messageID = null, messageText, timeCreated,repliedMessageID=null,attachments={}){
    const cidElem = document.getElementById(cid);
    if(cidElem){
        const cidList = cidElem.getElementsByClassName('card-body')[0].getElementsByClassName('chat-list')[0]
        if(cidList){
            let userData;
            const isMine = userID === currentUser['_id']
            if(isMine) {
                userData = currentUser;
            }else{
                userData = await getUserData(userID);
            }
            if(!messageID) {
                messageID = generateUUID();
            }
            let messageHTML = buildUserMessage(userData, messageID, messageText, timeCreated, isMine, repliedMessageID);
            messageHTML = addMessageAttachments(messageHTML, attachments);
            const blankChat = cidList.getElementsByClassName('blank_chat');
            if(blankChat.length>0){
                cidList.removeChild(blankChat[0]);
            }
            cidList.insertAdjacentHTML('beforeend', messageHTML);
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
 * @param repliedMessageID: id of replied message if any
 * @returns {string}: constructed HTML out of input params
 */
function buildUserMessage(userData, messageID, messageText, timeCreated, isMine, repliedMessageID=null){
    let html = "";
    const messageSideClass = isMine?"in":"out";
    //const messageTime = getTimeFromTimestamp(timeCreated);
    const avatarImage = userData.hasOwnProperty('avatar')?userData['avatar']:'default_avatar.png'
    html += `<li class="${messageSideClass}">`
    html += "<div class=\"chat-img\">\n" +
            `   <img alt="Avatar" src="${configData["imageBaseFolder"]+'/'+avatarImage}">\n` +
            "</div>"
    html +=` <div class="chat-body">
                <div class="chat-message" id="${messageID}">
                    <small style="font-size: small">${userData['nickname']}</small>
                    <p>${messageText}</p>
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
            const repliedText = repliedElem.getElementsByTagName('p')[0].innerText;
            const replyHTML = `<a class="reply-text" data-replied-id="${repliedID}">
                                    ${repliedText}
                                </a>`;
            document.getElementById(replyID).insertAdjacentHTML('afterbegin', replyHTML);
        }
    }
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
            replyItem.addEventListener('click', (e)=>{
               document.getElementById(replyItem.getAttribute('data-replied-id')).scrollIntoView();
            });
        });
    }
}

function buildConversation(conversationData,remember=true){
   if(remember){
       addNewCID(conversationData['_id'], conversationAlignmentKey);
   }
   const newConversationHTML = buildConversationHTML(conversationData);
   const conversationsBody = document.getElementById('conversationsBody');
   conversationsBody.insertAdjacentHTML('afterbegin', newConversationHTML);
   attachReplies(conversationData);
   const currentConversation = document.getElementById(conversationData['_id']);
   const conversationParent = currentConversation.parentElement;
   const conversationHolder = conversationParent.parentElement;
   const chatInputButton = document.getElementById(conversationData['_id']+'-send');
    if(chatInputButton.hasAttribute('data-target-cid')) {
        chatInputButton.addEventListener('click', (e)=>{
            const textInputElem = document.getElementById(conversationData['_id']+'-input');
            emitUserMessage(textInputElem, e.target.getAttribute('data-target-cid'));
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
}

function buildConversationHTML(conversationData = {}){
    let html = `<div class="conversationContainer col-xl-6 col-lg-6 col-md-6 col-sm-12 col-12 m-2">
                <div class="card" id="${ conversationData['_id'] }">
                    <div class="card-header">${ conversationData['conversation_name'] }
                        <button type="button" id="close-${conversationData['_id']}" data-target-cid="${conversationData['_id']}" class="close-cid">
                            <span aria-hidden="true">×</span>
                        </button>
                    </div>
                    <div class="card-body height3" style="overflow-y: auto; height: 450px!important;">
                        <ul class="chat-list">`
    if(conversationData.hasOwnProperty('chat_flow')) {
        Array.from(conversationData['chat_flow']).forEach(message => {
            const isMine = currentUser && message['user_nickname'] === currentUser['nickname'];
            html += buildUserMessage({'avatar':message['user_avatar'],'nickname':message['user_nickname']},message['message_id'], message['message_text'], getTimeFromTimestamp(message['created_on']),isMine,
                message?.replied_message);
        });
    }else{
        html+=`<div class="blank_chat">No messages in this chat yet...</div>`;
    }
    html += `</ul>
             </div>
                   <div class="card-footer">
                        <input class="user_input form-control" id="${conversationData['_id']}-input" type="text" placeholder='Write a Message to "${conversationData['conversation_name']}"'>
                        <button class="send_user_input mt-2 btn btn-success" id="${conversationData['_id']}-send" data-target-cid="${conversationData['_id']}">Send Message</button>
                    </div>
                </div>
            </div>`
    return html;
}


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



function addMessageAttachments(html, attachments={}){
    return html;
}

function getTimeFromTimestamp(timeCreated){
    const date = new Date(timeCreated * 1000);
    const hours = date.getHours();
    const minutes = "0" + date.getMinutes();
    return hours + ':' + minutes.substr(-2);
}

function emitUserMessage(textInputElem, cid, repliedMessageID=null){
    if(textInputElem && textInputElem.value){
        const timeCreated = Math.floor(Date.now() / 1000);
        const messageText = textInputElem.value;
        addMessage(cid, currentUser['_id'],null, messageText, timeCreated,repliedMessageID,{}, true).then(messageID=>{
            socket.emit('user_message', {'cid':cid,'userID':currentUser['_id'],
                              'messageText':messageText,
                              'messageID':messageID,
                              'timeCreated':timeCreated});
        });
        textInputElem.value = "";
    }
}

function retrieveItemsLayout(keyName=conversationAlignmentKey){
    let itemsLayout = localStorage.getItem(keyName);
    if(itemsLayout){
        itemsLayout = JSON.parse(itemsLayout);
    }else{
        itemsLayout = [];
    }
    return itemsLayout;
}

function addNewCID(cid, keyName=conversationAlignmentKey){
    let itemLayout = retrieveItemsLayout(keyName);
    itemLayout.push(cid);
    localStorage.setItem(keyName,JSON.stringify(itemLayout));
}

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
                displayAlert('conversationsBody','No matching conversation found','danger');
                removeCID(item);
            }
        });
    }
}

function refreshChat(){
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
                    displayAlert('importConversationModalBody','Cannot find conversation matching your search','danger');
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
                    displayAlert('newConversationModalBody','Cannot add new conversation: '+ responseJson['detail'][0]['msg'],'danger');
                }
                newConversationName.value="";
                newConversationID.value = "";
                isPrivate.checked = false;
            });
    });
});
