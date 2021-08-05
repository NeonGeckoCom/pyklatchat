const avatarPath = '../../static/img/';
const currentUser = get_user_data();

function addMessage(cid, userID, messageText, timeCreated,attachments={}, isMine=true){
    const cidElem = document.getElementById(cid);
    if(cidElem){
        const cidList = cidElem.getElementsByClassName('card-body')[0].getElementsByClassName('chat-list')[0]
        if(cidList){
            const userData = get_user_data(userID);
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
                    <h5>${userData['first_name']} ${userData['last_name']}</h5>
                    <p>${messageText}</p>
                </div>
             </div>`
    html+="</li>"
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
        const timeCreated = Math.floor(Date.now() / 1000)
        addMessage(cid, currentUser['_id'], textInputElem.value, timeCreated,{}, true);
        socket.emit('user_message', {'cid':cid,'userID':currentUser['_id'],'messageText':textInputElem.value,'timeCreated':timeCreated});
        textInputElem.value = "";
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
