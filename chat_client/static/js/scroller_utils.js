/**
 * Decides whether scrolling on new message is required based on the current viewport
 * @param messageList: message list DOM element
 * @param lastNElements: number of last elements to consider a live following
 */
function scrollOnNewMessage(messageList, lastNElements=3){
    // If we see last element of the chat - we are following it
    for (let i = 1; i <= lastNElements; i++) {
        if (isInViewport(messageList.children[messageList.children.length - i])){
            messageList.lastChild.scrollIntoView();
            return
        }
    }
}