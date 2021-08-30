const conversationSearchInput = document.getElementById('conversationSearchInput');
const addBySearch = document.getElementById('addBySearch');
const addNewConversation = document.getElementById('addNewConversation');
const conversationBody = document.getElementById('conversationsBody');

async function addMessage(cid, userID=null, messageID = null, messageText, timeCreated,attachments={}){
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
            let messageHTML = buildUserMessage(userData, messageID, messageText, timeCreated, isMine);
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

function buildUserMessage(userData, messageID, messageText, timeCreated, isMine){
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
                    <small>${userData['nickname']}</small>
                    <p>${messageText}</p>
                </div>
             </div>`
    html+="</li>"
    return html;
}

function buildConversation(conversationData,remember=true){
   if(remember){
       addNewCID(conversationData['_id'], conversationAlignmentKey);
   }
   const newConversationHTML = buildConversationHTML(conversationData);
   const conversationsBody = document.getElementById('conversationsBody');
   conversationsBody.insertAdjacentHTML('afterbegin', newConversationHTML);
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
                    <div class="card-body height3" style="overflow-y: auto; height: 250px!important;">
                        <ul class="chat-list">`
    if(conversationData.hasOwnProperty('chat_flow')) {
        Array.from(conversationData['chat_flow']).forEach(message => {
            const orientation = currentUser && message['user_nickname'] === currentUser['nickname']?'in':'out';
            html += `<li class="${orientation}" data-sender="${ message['user_nickname'] }">
                        <div class="chat-img">
                            <img alt="Avatar" src="${ configData.imageBaseFolder+'/'+message['user_avatar'] }">
                        </div>
                        <div class="chat-body" id="${ message['message_id'] }">
                            <div class="chat-message">
                                <h5>${ message['user_nickname'] }</h5>
                                <p>${ message['message_text'] }</p>
                            </div>
                        </div>
                    </li>`
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

function emitUserMessage(textInputElem, cid){
    if(textInputElem && textInputElem.value){
        const timeCreated = Math.floor(Date.now() / 1000);
        const messageText = textInputElem.value;
        addMessage(cid, currentUser['_id'],null, messageText, timeCreated,{}, true).then(messageID=>{
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
