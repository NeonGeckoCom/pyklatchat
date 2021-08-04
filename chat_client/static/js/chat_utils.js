function addMessage(cid, userData, messageText, attachments={}, isMine=true){
    const cidElem = document.getElementById(cid);
    if(!cidElem){
        console.error(`cid: ${cid} does not exist in current DOM`);
    }

}

function handleMessageAttachments(attachments={}){
    return 'Not Implemented';
}