const importConversationModal = $('#importConversationModal');
const conversationSearchInput = document.getElementById('conversationSearchInput');
const addBySearch = document.getElementById('addBySearch');

const newConversationModal = $('#newConversationModal');
const addNewConversation = document.getElementById('addNewConversation');

const conversationBody = document.getElementById('conversationsBody');

let conversationState = {};

/**
 * Gets participants data listed under conversation id
 * @param cid: target conversation id
 * @return {*} participants data object
 */
const getParticipants = (cid) => {
    return setDefault(setDefault(conversationState, cid, {}), 'participants', {});
}

/**
 * Sets participants count for conversation view
 * @param cid: desired conversation id
 */
const displayParticipantsCount = (cid) => {
    const participantsCountNode = document.getElementById(`participants-count-${cid}`);
    participantsCountNode.innerText = Object.keys(getParticipants(cid)).length;
}

/**
 * Adds new conversation participant
 * @param cid: conversation id
 * @param nickname: nickname to add
 * @param updateCount: to update participants count
 */
const addConversationParticipant = (cid, nickname, updateCount = false) => {
    const conversationParticipants = getParticipants(cid);
    if(!conversationParticipants.hasOwnProperty(nickname)){
        conversationParticipants[nickname] = {'num_messages': 1};
    }else{
        conversationParticipants[nickname]['num_messages']++;
    }
    if(updateCount){
        displayParticipantsCount(cid);
    }
}

/**
 * Saves attached files to the server
 * @param cid: target conversation id
 * @return attachments array or -1 if something went wrong
 */
const saveAttachedFiles = async (cid) => {
    const filesArr = getUploadedFiles(cid);
    const attachments = [];
    if (filesArr.length > 0){
        setChatState(cid, 'updating', 'Saving attachments...');
        let errorOccurred = null;
        const formData = new FormData();
        const attachmentProperties = {}
        filesArr.forEach(file=>{
            const generatedFileName = `${generateUUID(10,'00041000')}.${file.name.split('.').pop()}`;
            attachmentProperties[generatedFileName] = {'size': file.size, 'type': file.type}
            const renamedFile = new File([file], generatedFileName, {type: file.type});
            formData.append('files', renamedFile);
        });
        cleanUploadedFiles(cid);

        await fetchServer(`files/attachments`, REQUEST_METHODS.POST, formData)
            .then(async response => {
                const responseJson = await response.json();
                if (response.ok){
                    for (const [fileName, savedName] of Object.entries(responseJson['location_mapping'])){
                        attachments.push({'name': savedName,
                                          'size': attachmentProperties[fileName].size,
                                          'mime': attachmentProperties[fileName].type})
                    }
                }else{
                    throw `Failed to save attachments status=${response.status}, msg=${responseJson}`;
                }
            }).catch(err=>{
                errorOccurred=err;
            });
        if(errorOccurred){
            console.error(`Error during attachments preparation: ${errorOccurred}, skipping message sending`);
            return -1
        }else{
            console.log('Received attachments array: ', attachments);
        }
    }
    return attachments;
}

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
 *         'is_audio': true if message is an audio message
 *         'is_announcement': true if message is considered to be an announcement
 *         'created_on': 'creation time of the message'
 *     }, ... (num of user messages returned)]
 * }
 * @param conversationParentID: ID of conversation parent
 * @param remember: to store this conversation into localStorage (defaults to true)
 *
 * @return id of the built conversation
 */
async function buildConversation(conversationData={}, remember=true,conversationParentID = 'conversationsBody'){
   if(remember){
       addNewCID(conversationData['_id']);
   }
   if(configData.client === CLIENTS.MAIN) {
       getParticipants(conversationData['_id']);
   }
   const newConversationHTML = await buildConversationHTML(conversationData);
   const conversationsBody = document.getElementById(conversationParentID);
   conversationsBody.insertAdjacentHTML('afterbegin', newConversationHTML);
   initMessages(conversationData);

   const currentConversation = document.getElementById(conversationData['_id']);
   const conversationParent = currentConversation.parentElement;
   const conversationHolder = conversationParent.parentElement;

   const chatInputButton = document.getElementById(conversationData['_id']+'-send');
   const filenamesContainer = document.getElementById(`filename-container-${conversationData['_id']}`)
   const attachmentsButton = document.getElementById('file-input-'+conversationData['_id']);

    if(chatInputButton.hasAttribute('data-target-cid')) {
        chatInputButton.addEventListener('click', async (e)=>{
            const attachments = await saveAttachedFiles(conversationData['_id']);
            const textInputElem = document.getElementById(conversationData['_id']+'-input');
            if(Array.isArray(attachments)) {
                emitUserMessage(textInputElem, conversationData['_id'], null, attachments, '0', '0');
            }
            textInputElem.value = "";
        });
    }

    const chatCloseButton = document.getElementById(`close-${conversationData['_id']}`);
    if(chatCloseButton.hasAttribute('data-target-cid')) {
        chatCloseButton.addEventListener('click', (e)=>{
            conversationHolder.removeChild(conversationParent);
            removeConversation(conversationData['_id']);
        });
    }

    attachmentsButton.addEventListener('change', (e)=>{
        e.preventDefault();
        const fileName = getFilenameFromPath(e.currentTarget.value);
        const lastFile = attachmentsButton.files[attachmentsButton.files.length - 1]
        if(lastFile.size > configData['maxUploadSize']){
            console.warn(`Uploaded file is too big`);
        }else {
            addUpload(attachmentsButton.parentNode.parentNode.id, lastFile);
            filenamesContainer.insertAdjacentHTML('afterbegin',
                `<span class='filename'>${fileName}</span>`);
            filenamesContainer.style.display = "";
            if (filenamesContainer.children.length === configData['maxNumAttachments']) {
                attachmentsButton.disabled = true;
            }
        }
    });
    displayParticipantsCount(conversationData['_id']);
    await initLanguageSelectors(conversationData['_id']);
    setTimeout(() => getMessageListContainer(conversationData['_id']).lastElementChild?.scrollIntoView(true), 0);
    await addRecorder(conversationData);
    $('#copyrightContainer').css('position', 'inherit');
    return conversationData['_id'];
}

/**
 * Gets conversation data based on input string
 * @param input: input string text
 * @param firstMessageID: id of the the most recent message
 * @param maxResults: max number of messages to fetch
 * @returns {Promise<{}>} promise resolving conversation data returned
 */
async function getConversationDataByInput(input="", firstMessageID=null, maxResults=10){
    let conversationData = {};
    if(input && typeof input === "string"){
        let query_url = `chat_api/search/${input}?limit_chat_history=${maxResults}`
        if(firstMessageID){
            query_url += `&first_message_id=${firstMessageID}`
        }
        await fetchServer(query_url)
            .then(response => {
                if(response.ok){
                    return response.json();
                }else{
                    throw response.statusText;
                }
            })
            .then(data => {
                if (getUserMessages(data).length < maxResults){
                    console.log('All of the messages are already displayed');
                    setDefault(setDefault(conversationState, data['_id'], {}), 'all_messages_displayed', true);
                }
                conversationData = data;
            }).catch(err=> console.warn('Failed to fulfill request due to error:',err));
    }
    return conversationData;
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
 */
function addNewCID(cid){
    const keyName = conversationAlignmentKey;
    let itemLayout = retrieveItemsLayout(keyName);
    itemLayout.push(cid);
    localStorage.setItem(keyName,JSON.stringify(itemLayout));
}

/**
 * Removed conversation id from local storage
 * @param cid: conversation id to remove
 */
function removeConversation(cid){
    const keyName = conversationAlignmentKey;
    let itemLayout = retrieveItemsLayout(keyName);
    itemLayout = itemLayout.filter(function(value, index, arr){
        return value !== cid;
    });
    if (itemLayout.length === 0){
        $('#copyrightContainer').css('position', 'absolute');
    }
    localStorage.setItem(keyName,JSON.stringify(itemLayout));
}

/**
 * Checks if cid is in local storage
 * @param cid
 * @return true if cid is displayed, false otherwise
 */
function isDisplayed(cid){
    return retrieveItemsLayout().includes(cid);
}

/**
 * Custom Event fired on supported languages init
 * @type {CustomEvent<string>}
 */
const chatAlignmentRestoredEvent = new CustomEvent("chatAlignmentRestored", { "detail": "Event that is fired when chat alignment is restored" });

/**
 * Restores chats alignment from the local storage
 *
 * @param keyName: name of the local storage key
**/
async function restoreChatAlignment(keyName=conversationAlignmentKey){
    let itemsLayout = retrieveItemsLayout(keyName);
    for (const item of itemsLayout) {
        await getConversationDataByInput(item).then(async conversationData=>{
            if(conversationData && Object.keys(conversationData).length > 0) {
                await buildConversation(conversationData, false);
            }else{
                displayAlert(document.getElementById('conversationsBody'),'No matching conversation found','danger', 'noRestoreConversationAlert', {'type': alertBehaviors.AUTO_EXPIRE});
                removeConversation(item);
            }
        });
    }
    console.log('Chat Alignment Restored');
    await requestChatsLanguageRefresh();
    document.dispatchEvent(chatAlignmentRestoredEvent);
}


/**
 * Helper struct to decide on which kind of messages to refer
 * "all" - all the messages
 * "mine" - only the messages emitted by current user
 * "others" - all the messages except "mine"
 */
const MESSAGE_REFER_TYPE = {
    ALL: 'all',
    MINE: 'mine',
    OTHERS: 'other'
}

/**
 * Gets array of messages for provided conversation id
 * @param cid: target conversation id
 * @param messageReferType: message refer type to consider from MESSAGE_REFER_TYPE
 * @param idOnly: to return id only (defaults to false)
 * @return array of message DOM objects under given conversation
 */
function getMessagesOfCID(cid, messageReferType=MESSAGE_REFER_TYPE.ALL, idOnly=false){
    let messages = []
    const messageContainer =getMessageListContainer(cid);
    if(messageContainer){
        const listItems = messageContainer.getElementsByTagName('li');
        Array.from(listItems).forEach(li=>{
           try {
               const messageNode = li.getElementsByClassName('chat-body')[0].getElementsByClassName('chat-message')[0];
               // console.debug(`pushing shout_id=${messageNode.id}`);
               if (messageReferType === MESSAGE_REFER_TYPE.ALL ||
                   (messageReferType === MESSAGE_REFER_TYPE.MINE && messageNode.getAttribute('data-sender') === currentUser['nickname']) ||
                   (messageReferType === MESSAGE_REFER_TYPE.OTHERS && messageNode.getAttribute('data-sender') !== currentUser['nickname'])){
                   if (idOnly){
                       messages.push(messageNode.id);
                   }else {
                       messages.push(messageNode);
                   }
               }
           } catch (e) {
               console.warn(`Failed to get message under node: ${li} - ${e}`);
           }
        });
    }
    return messages;
}

/**
 * Refreshes chat view (e.g. when user session gets updated)
 */
function refreshChatView(){
    Array.from(conversationBody.getElementsByClassName('conversationContainer')).forEach(async conversation=>{
       const messages = getMessagesOfCID(conversation.id);
       Array.from(messages).forEach(message=>{
          if(message.hasAttribute('data-sender')){
              const messageSenderNickname = message.getAttribute('data-sender');
              console.log(`messageSenderNickname=${messageSenderNickname}`)
              message.className = currentUser && messageSenderNickname === currentUser['nickname']?'in':'out';
          }
       });
    });
}

/**
 * Gets all opened chats
 * @return {[]} list of displayed chat ids
 */
function getOpenedChats(){
    let cids = [];
    Array.from(conversationBody.getElementsByClassName('conversationContainer')).forEach(conversationContainer=>{
        cids.push(conversationContainer.getElementsByClassName('card')[0].id);
    });
    return cids;
}

const CHAT_STATES = ['active', 'updating'];

/**
 * Sets state to the desired cid
 * @param cid: desired conversation id
 * @param state: desired state
 * @param state_msg: message following state transition (e.g. why chat is updating)
 */
function setChatState(cid, state='active', state_msg = ''){

    console.log(`cid=${cid}, state=${state}, state_msg=${state_msg}`)
    if (!CHAT_STATES.includes(state)){
        console.error(`Invalid transition state provided, should be one of ${CHAT_STATES}`);
        return -1;
    }else{
        const cidNode = document.getElementById(cid);
        const spinner = document.getElementById(`${cid}-spinner`);
        const spinnerUpdateMsg = document.getElementById(`${cid}-update-msg`);
        if (state === 'updating'){
            cidNode.classList.add('chat-loading');
            spinner.style.setProperty('display', 'flex', 'important');
            spinnerUpdateMsg.innerHTML = state_msg;
        }else if(state === 'active'){
            cidNode.classList.remove('chat-loading');
            spinner.style.setProperty('display', 'none', 'important');
            spinnerUpdateMsg.innerHTML = '';
        }
        conversationState[cid]['state'] = state;
        conversationState[cid]['state_message'] = state_msg;
    }
}

/**
 * Displays first conversation matching search string
 * @param searchStr: Search string to find matching conversation
 * @param alertParentID: id of the element to display alert in
 */
async function displayConversation(searchStr, alertParentID = null){
    if (searchStr !== "") {
        const alertParent = document.getElementById(alertParentID);
        await getConversationDataByInput(searchStr).then(async conversationData => {
            let responseOk = false;
            if (getOpenedChats().includes(conversationData['_id']) && alertParent) {
                displayAlert(alertParent, 'Chat is already displayed', 'danger');
            } else if (conversationData && Object.keys(conversationData).length > 0) {
                await buildConversation(conversationData);
                for (const inputType of ['incoming', 'outcoming']){
                    requestTranslation(conversationData['_id'], null, null, inputType);
                }
                responseOk = true;
            } else {
                if (alertParent) {
                    displayAlert(
                        alertParent,
                        'Cannot find conversation matching your search',
                        'danger',
                        'noSuchConversationAlert',
                        {'type': alertBehaviors.AUTO_EXPIRE}
                        );
                }
            }
            return responseOk;
        });
    }
}

/**
 * Handles requests on creation new conversation by the user
 * @param conversationName: New Conversation Name
 * @param isPrivate: if conversation should be private (defaults to false)
 * @param conversationID: New Conversation ID (optional)
 */
async function createNewConversation(conversationName, isPrivate=false, conversationID=null) {

    let formData = new FormData();

    formData.append('conversation_name', conversationName);
    formData.append('conversation_id', conversationID);
    formData.append('is_private', isPrivate)

    await fetchServer(`chat_api/new`,  REQUEST_METHODS.POST, formData).then(async response => {
        const responseJson = await response.json();
        let responseOk = false;
        if (response.ok) {
            await buildConversation(responseJson).then(async cid=>{
                await initLanguageSelectors(cid);
                console.log(`inited language selectors for ${cid}`);
            });
            responseOk = true
        } else {
            displayAlert(document.getElementById('newConversationModalBody'),
                `${responseJson['msg']}`,
                'danger');
        }
        return responseOk;
    });
}

document.addEventListener('DOMContentLoaded', (e)=>{

    document.addEventListener('supportedLanguagesLoaded', async (e)=>{
        await refreshCurrentUser(false).then(async _=>await restoreChatAlignment()).then(async _=> await refreshChatView(true));
    });

    if (configData['client'] === CLIENTS.MAIN) {
        addBySearch.addEventListener('click', async (e) => {
            e.preventDefault();
            displayConversation(conversationSearchInput.value, 'importConversationModalBody').then(responseOk=> {
                conversationSearchInput.value = "";
                if(responseOk) {
                    importConversationModal.modal('hide');
                }
            });
        });
        addNewConversation.addEventListener('click', async (e) => {
            e.preventDefault();
            const newConversationID = document.getElementById('conversationID');
            const newConversationName = document.getElementById('conversationName');
            const isPrivate = document.getElementById('isPrivate');
            createNewConversation(newConversationName.value, isPrivate.checked, newConversationID ? newConversationID.value : null).then(responseOk=>{
                newConversationName.value = "";
                newConversationID.value = "";
                isPrivate.checked = false;
                if(responseOk) {
                    newConversationModal.modal('hide');
                }
            });
        });
    }
});
