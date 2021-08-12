const avatarPath = '../../static/img/';

async function addMessage(cid, userID=null, messageText, timeCreated,attachments={}){
    const cidElem = document.getElementById(cid);
    if(cidElem){
        const cidList = cidElem.getElementsByClassName('card-body')[0].getElementsByClassName('chat-list')[0]
        if(cidList){
            let userData;
            const isMine = userID === currentUser['_id']
            if(isMine) {
                userData = currentUser;
            }else{
                userData = await get_user_data(userID);
            }
            let messageHTML = buildUserMessage(userData, messageText, timeCreated, isMine);
            messageHTML = addMessageAttachments(messageHTML, attachments);
            const blankChat = cidList.getElementsByClassName('blank_chat');
            if(blankChat.length>0){
                cidList.removeChild(blankChat[0]);
            }
            cidList.insertAdjacentHTML('beforeend', messageHTML);
        }
    }
}

function buildUserMessage(userData, messageText, timeCreated, isMine){
    let html = "";
    const messageSideClass = isMine?"in":"out";
    //const messageTime = getTimeFromTimestamp(timeCreated);
    const avatarImage = userData.hasOwnProperty('avatar')?userData['avatar']:'default_avatar.png'
    html += `<li class="${messageSideClass}">`
    html += "<div class=\"chat-img\">\n" +
            `   <img alt="Avatar" src="${avatarPath+avatarImage}">\n` +
            "</div>"
    html +=` <div class="chat-body">
                <div class="chat-message">
                    <h5>${userData['nickname']}</h5>
                    <p>${messageText}</p>
                </div>
             </div>`
    html+="</li>"
    return html;
}

function buildConversation(conversationData = {}){
    let html = `<div class="conversationContainer col-xl-6 col-lg-6 col-md-6 col-sm-12 col-12">
                <div class="card" id="{{ conversation['_id'] }}">
                    <div class="card-header">${ conversationData['conversation_name'] }</div>
                    <div class="card-body height3">
                        <ul class="chat-list">`
    if(conversationData.hasOwnProperty('chat_flow')) {
        Array.from(conversationData['chat_flow']).forEach(message => {
            const orientation = currentUser && message['user_nickname'] === currentUser['nickname']?'in':'out';
            html += `<li class="${orientation}">
                        <div class="chat-img">
                            <img alt="Avatar" src="../../static/img/${ message['user_avatar'] }">
                        </div>
                        <div class="chat-body">
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
                        <input class="user_input form-control" data-target-cid="${conversationData['_id']}" type="text" placeholder='Write a Message to "${conversationData['conversation_name']}"'>
                        <button class="send_user_input mt-2 btn btn-success" data-target-cid="${conversationData['_id']}">Send Message</button>
                    </div>
                </div>
            </div>`
    return html;
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
        addMessage(cid, currentUser['_id'], textInputElem.value, timeCreated,{}, true).then(_=>{
            socket.emit('user_message', {'cid':cid,'userID':currentUser['_id'],'messageText':textInputElem.value,'timeCreated':timeCreated});
            textInputElem.value = "";
        });
    }
}

document.addEventListener('DOMContentLoaded', (e)=>{
   const chatInputButtons = document.getElementsByClassName('send_user_input');
   Array.from(chatInputButtons).forEach(btn=>{
        if(btn.hasAttribute('data-target-cid')) {
            btn.addEventListener('click', (e)=>{
                const textInputElem = btn.parentElement.getElementsByClassName('user_input')[0];
                emitUserMessage(textInputElem, btn.getAttribute('data-target-cid'));
            });
        }
   });
});
