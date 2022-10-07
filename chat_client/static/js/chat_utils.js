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

const CONVERSATION_SKINS = {
    BASE: 'base',
    PROMPTS: 'prompts'
}

let holdTimer = 0;


const startTimer = () => {
    holdTimer =Date.now();
}

const stopTimer = () => {
    const timeDue = Date.now() - holdTimer;
    holdTimer = 0;
    return timeDue;
}

const startSelection = (table, exportToExcelBtn) => {
    table.classList.remove('selected');
    const container = table.parentElement.parentElement;
    if(Array.from(container.getElementsByClassName('selected')).length === 0){
       exportToExcelBtn.disabled = true;
    }
    startTimer();
}

const selectTable = (table, exportToExcelBtn) => {
    const timePassed = stopTimer();
    if (timePassed >= 300){
      exportToExcelBtn.disabled = false;
      table.classList.add('selected');
    }
}


function exportTablesToExcel(tables, filePrefix = 'table_export') {

    const exportTable = new TableExport(table, {formats:['xlsx'],filename: "test_export",sheet_name: 'Test_Sheet', bootstrap: true, exportButtons: false});
    const exportData = exportTable.getExportData();
    const xlsxData = exportData[table.id].xlsx;
    exportTable.export2file(xlsxData.data, xlsxData.mimeType, xlsxData.filename, xlsxData.fileExtension, xlsxData.merges, xlsxData.RTL, xlsxData.sheetname)
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
 * @param skin: Conversation skin to build
 *
 * @return id of the built conversation
 */
async function buildConversation(conversationData={}, skin = CONVERSATION_SKINS.BASE, remember=true,conversationParentID = 'conversationsBody'){
    const idField = '_id';
    const cid = conversationData[idField];
    if (!cid){
        console.error(`Failed to extract id field="${idField}" from conversation data - ${conversationData}`);
        return -1;
    }
    if(remember){
       addNewCID(cid, skin);
    }
    const newConversationHTML = await buildConversationHTML(conversationData, skin);
    const conversationsBody = document.getElementById(conversationParentID);
    conversationsBody.insertAdjacentHTML('afterbegin', newConversationHTML);
    initMessages(conversationData, skin);

    const messageListContainer = getMessageListContainer(cid);
    const currentConversation = document.getElementById(cid);
    const conversationParent = currentConversation.parentElement;
    const conversationHolder = conversationParent.parentElement;

    let chatCloseButton = document.getElementById(`close-${cid}`);

    if (skin === CONVERSATION_SKINS.BASE) {

       const chatInputButton = document.getElementById(conversationData['_id'] + '-send');
       const filenamesContainer = document.getElementById(`filename-container-${conversationData['_id']}`)
       const attachmentsButton = document.getElementById('file-input-' + conversationData['_id']);

       if (chatInputButton.hasAttribute('data-target-cid')) {
           chatInputButton.addEventListener('click', async (e) => {
               const attachments = await saveAttachedFiles(conversationData['_id']);
               const textInputElem = document.getElementById(conversationData['_id'] + '-input');
               if (Array.isArray(attachments)) {
                   emitUserMessage(textInputElem, conversationData['_id'], null, attachments, '0', '0');
               }
               textInputElem.value = "";
           });
       }

       attachmentsButton.addEventListener('change', (e) => {
           e.preventDefault();
           const fileName = getFilenameFromPath(e.currentTarget.value);
           const lastFile = attachmentsButton.files[attachmentsButton.files.length - 1]
           if (lastFile.size > configData['maxUploadSize']) {
               console.warn(`Uploaded file is too big`);
           } else {
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

       const promptModeButton = document.getElementById(`prompt-mode-${conversationData['_id']}`);

       promptModeButton.addEventListener('click', async (e) => {
           e.preventDefault();
           chatCloseButton.click();
           await displayConversation(conversationData['_id'], CONVERSATION_SKINS.PROMPTS)
       });
    }
    else if (skin === CONVERSATION_SKINS.PROMPTS) {
       chatCloseButton = document.getElementById(`close-prompts-${cid}`);
       const baseModeButton = document.getElementById(`base-mode-${cid}`);
       const exportToExcelBtn = document.getElementById(`${cid}-export-to-excel`)

       // TODO: fix here to use prompt- prefix
       baseModeButton.addEventListener('click', async (e) => {
           e.preventDefault();
           chatCloseButton.click();
           await displayConversation(cid, CONVERSATION_SKINS.BASE);
       });

       // TODO: make an array of prompt tables only in dedicated conversation
       Array.from(getMessagesOfCID(cid, MESSAGE_REFER_TYPE.ALL, skin, false)).forEach(table => {

           table.addEventListener('mousedown', (_) => startSelection(table, exportToExcelBtn));
           table.addEventListener('touchstart', (_) => startSelection(table, exportToExcelBtn));
           table.addEventListener('mouseup', (_) => selectTable(table, exportToExcelBtn));
           table.addEventListener("touchend", (_) => selectTable(table, exportToExcelBtn));

       });
       exportToExcelBtn.addEventListener('click', (e)=>{
           exportTablesToExcel(messageListContainer.getElementsByClassName('selected'));
       });
    }

    if (chatCloseButton.hasAttribute('data-target-cid')) {
       chatCloseButton.addEventListener('click', (e) => {
           conversationHolder.removeChild(conversationParent);
           removeConversation(cid);
       });
    }
    // $('#copyrightContainer').css('position', 'inherit');
    return cid;
}

/**
 * Gets conversation data based on input string
 * @param input: input string text
 * @param firstMessageID: id of the the most recent message
 * @param skin: resolves by server for which data to return
 * @param maxResults: max number of messages to fetch
 * @returns {Promise<{}>} promise resolving conversation data returned
 */
async function getConversationDataByInput(input="", skin=CONVERSATION_SKINS.BASE, firstMessageID=null, maxResults=10){
    let conversationData = {};
    if(input && typeof input === "string"){
        // TODO: add skin resolver
        let query_url = `chat_api/search/${input}?limit_chat_history=${maxResults}&skin=${skin}`;
        if(firstMessageID){
            query_url += `&first_message_id=${firstMessageID}`;
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
    const itemsLayout = localStorage.getItem(keyName);
    return itemsLayout?JSON.parse(itemsLayout): {};
}

/**
 * Adds new conversation id to local storage
 * @param cid: conversation id to add
 * @param skin: conversation skin to add
 */
function addNewCID(cid, skin){
    const keyName = conversationAlignmentKey;
    let itemLayout = retrieveItemsLayout(keyName) || {};
    itemLayout[cid] = {'skin': skin, 'added_on': getCurrentTimestamp()};
    localStorage.setItem(keyName,JSON.stringify(itemLayout));
}

/**
 * Removed conversation id from local storage
 * @param cid: conversation id to remove
 */
function removeConversation(cid){
    const keyName = conversationAlignmentKey;
    let itemLayout = retrieveItemsLayout(keyName);
    delete itemLayout[cid];
    if (Object.keys(itemLayout).length === 0){
        $('#copyrightContainer').css('position', 'absolute');
    }
    localStorage.setItem(keyName,JSON.stringify(itemLayout));
}

/**
 * Checks if conversation is displayed
 * @param cid: target conversation id
 * @return true if cid is displayed, false otherwise
 */
function isDisplayed(cid){
    return Object.keys(retrieveItemsLayout()).includes(cid);
}

/**
 * Gets value of desired property in stored conversation
 * @param cid: target conversation id
 * @param key: key of stored conversation
 * @param defaultValue: default value to return
 * @return true if cid is displayed, false otherwise
 */
function getCIDStoreProperty(cid, key, defaultValue=null){
    if (key === 'skin'){
        defaultValue = CONVERSATION_SKINS.BASE;
    }
    return setDefault(setDefault(retrieveItemsLayout(), cid, {}), key, defaultValue);
}

/**
 * Sets new skin value to the selected conversation
 * @param cid: target conversation id
 * @param property: key of stored conversation
 * @param value: value to set
 */
function updateCIDStoreProperty(cid, property, value){
    const keyName = conversationAlignmentKey;
    let itemLayout = retrieveItemsLayout(keyName);
    setDefault(itemLayout, cid, {})[property] = value;
    localStorage.setItem(keyName,JSON.stringify(itemLayout));
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
    const itemsLayout = retrieveItemsLayout(keyName);
    const sortedEntries = Object.entries(itemsLayout).sort((a, b) => a[1]['added_on'] - b[1]['added_on'])
    for (const [cid, props] of sortedEntries) {
        const cidSkin = props?.skin;
        await getConversationDataByInput(cid, cidSkin).then(async conversationData=>{
            if(conversationData && Object.keys(conversationData).length > 0) {
                await buildConversation(conversationData, cidSkin, false);
            }else{
                displayAlert(document.getElementById('conversationsBody'),'No matching conversation found','danger', 'noRestoreConversationAlert', {'type': alertBehaviors.AUTO_EXPIRE});
                removeConversation(cid);
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
 * @param skin: conversation skin to apply
 * @return array of message DOM objects under given conversation
 */
function getMessagesOfCID(cid, messageReferType=MESSAGE_REFER_TYPE.ALL, skin=CONVERSATION_SKINS.BASE, idOnly=false){
    let messages = []
    const messageContainer =getMessageListContainer(cid);
    if(messageContainer){
        const listItems = messageContainer.getElementsByTagName('li');
        Array.from(listItems).forEach(li=>{
           try {
               const messageNode = getMessageNode(li, skin);
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
    Array.from(conversationBody.getElementsByClassName('conversationContainer')).forEach(conversation=>{
        const skin = getCIDStoreProperty(conversation.id, 'skin');
        if (skin === CONVERSATION_SKINS.BASE) {
            const messages = getMessagesOfCID(conversation.id);
            Array.from(messages).forEach(message => {
                const messageListNode = message.parentElement.parentElement;
                if (message.hasAttribute('data-sender')) {
                    const messageSenderNickname = message.getAttribute('data-sender');
                    messageListNode.className = currentUser && messageSenderNickname === currentUser['nickname'] ? 'in' : 'out';
                }
            });
        }
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
    // TODO: refactor this method to handle when there are multiple messages on a stack
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
 * @param skin: target conversation skin to display
 * @param alertParentID: id of the element to display alert in
 */
async function displayConversation(searchStr, skin=CONVERSATION_SKINS.BASE, alertParentID = null){
    if (searchStr !== "") {
        const alertParent = document.getElementById(alertParentID);
        await getConversationDataByInput(searchStr, skin).then(async conversationData => {
            let responseOk = false;
            if (isDisplayed(conversationData['_id'])) {
                displayAlert(alertParent, 'Chat is already displayed', 'danger');
            } else if (conversationData && Object.keys(conversationData).length > 0) {
                await buildConversation(conversationData, skin);
                for (const inputType of ['incoming', 'outcoming']){
                    requestTranslation(conversationData['_id'], null, null, inputType);
                }
                responseOk = true;
            } else {
                displayAlert(
                    alertParent,
                    'Cannot find conversation matching your search',
                    'danger',
                    'noSuchConversationAlert',
                    {'type': alertBehaviors.AUTO_EXPIRE}
                    );
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
            await buildConversation(responseJson, CONVERSATION_SKINS.BASE).then(async cid=>{
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
        await refreshCurrentUser(false).then(async _=>await restoreChatAlignment()).then(async _=> refreshChatView());
    });

    if (configData['client'] === CLIENTS.MAIN) {
        addBySearch.addEventListener('click', async (e) => {
            e.preventDefault();
            displayConversation(conversationSearchInput.value, CONVERSATION_SKINS.BASE, 'importConversationModalBody').then(responseOk=> {
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
