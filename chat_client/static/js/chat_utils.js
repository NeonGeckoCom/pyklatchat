const avatarPath = '../../static/img/'

function addMessage(cid, userID, messageText, timeCreated,attachments={}, isMine=true){
    const cidElem = document.getElementById(cid);
    if(cidElem){
        const cidList = cidElem.getElementsByClassName('card-body')[0].getElementsByClassName('chat-list')[0]
        if(cidList){
            const userData = get_user_data(userID);
            let messageHTML = buildUserMessage(userData, messageText, timeCreated, isMine);
            messageHTML = addMessageAttachments(messageHTML, attachments);
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