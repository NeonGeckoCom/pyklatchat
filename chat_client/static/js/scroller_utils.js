const MessageScrollPosition = {
  START: 'START',
  END: 'END',
  MIDDLE: 'MIDDLE',
};

/**
 * Gets current message list scroller position based on first and last n-items visibility
 * @param messageList: Container of messages
 * @param numElements: number of first and last elements to check for visibility
 * @param assertOnly: check only for one of the scroll position (preventing ambiguity if its a start or the end)
 * @return {string} MessageScrollPosition from Enum
 */
function getMessageScrollPosition(messageList, numElements=3, assertOnly=null){
    numElements = Math.min(messageList.children.length, numElements);
    if(numElements > 0) {
        for (let i = 1; i <= numElements; i++) {
            if (!(assertOnly === MessageScrollPosition.START) &&
                isInViewport(messageList.children[messageList.children.length - i])) {
                return MessageScrollPosition.END;
            }
            if (!(assertOnly === MessageScrollPosition.END) && isInViewport(messageList.children[i - 1])) {
                return MessageScrollPosition.START;
            }
        }
    }
    return MessageScrollPosition.MIDDLE;
}

/**
 * Decides whether scrolling on new message is required based on the current viewport
 * @param messageList: message list DOM element
 * @param lastNElements: number of last elements to consider a live following
 */
function scrollOnNewMessage(messageList, lastNElements=3){
    // If we see last element of the chat - we are following it
    if(getMessageScrollPosition(messageList, lastNElements, MessageScrollPosition.END) === MessageScrollPosition.END){
        messageList.lastChild.scrollIntoView();
    }
}