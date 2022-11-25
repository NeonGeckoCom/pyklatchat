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
            const replyHTML = `<i class="reply-text" data-replied-id="${repliedID}">
                                    ${repliedText}
                                </i>`;
            const replyPlaceholder = document.getElementById(replyID).getElementsByClassName('reply-placeholder')[0];
            replyPlaceholder.insertAdjacentHTML('afterbegin', replyHTML);
            attachReplyHighlighting(replyPlaceholder.getElementsByClassName('reply-text')[0]);
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
        getUserMessages(conversationData).forEach(message => {
            resolveUserReply(message['message_id'], message?.replied_message);
        });
        Array.from(document.getElementsByClassName('reply-text')).forEach(replyItem=>{
            attachReplyHighlighting(replyItem);
        });
    }
}
