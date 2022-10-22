const importConversationModal = $('#importConversationModal');
const conversationSearchInput = document.getElementById('conversationSearchInput');
const importConversationModalSuggestions = document.getElementById('importConversationModalSuggestions');

const addBySearch = document.getElementById('addBySearch');

const newConversationModal = $('#newConversationModal');
const addNewConversation = document.getElementById('addNewConversation');

const conversationBody = document.getElementById('conversationsBody');

let conversationState = {};

/**
 * Clears conversation state cache
 * @param cid: Conversation ID to clear
 */
const clearStateCache = (cid) => {
    delete conversationState[cid];
}

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
 * Supported conversation skins
 * @type Object
 */
const CONVERSATION_SKINS = {
    BASE: 'base',
    PROMPTS: 'prompts'
}

/**
 *
 * @param table
 * @param exportToExcelBtn
 */
const startSelection = (table, exportToExcelBtn) => {
    table.classList.remove('selected');
    const container = table.parentElement.parentElement;
    if(Array.from(container.getElementsByClassName('selected')).length === 0){
       exportToExcelBtn.disabled = true;
    }
    startTimer();
}


/**
 * Marks target table as selected
 * @param table: HTMLTable element
 * @param exportToExcelBtn: export to excel button (optional)
 */
const selectTable = (table, exportToExcelBtn=null) => {
    const timePassed = stopTimer();
    if (timePassed >= 300){
        if(exportToExcelBtn)
            exportToExcelBtn.disabled = false;
        table.classList.add('selected');
    }
}


/**
 * Wraps provided array of HTMLTable elements into XLSX file and exports it to the invoked user
 * @param tables: array of HTMLTable elements to export
 * @param filePrefix: prefix of the file name to be imported
 * @param sheetPrefix: prefix to apply for each sheet generated per HTMLTable
 */
function exportTablesToExcel(tables, filePrefix = 'table_export', sheetPrefix="") {
    const tablesData = [];
    const sheetNames = [];
    let xlsxData = null;
    tables = Array.from(tables);
    tables.forEach(table=>{
        const exportTable = new TableExport(table, {formats:['xlsx'],filename: "test_export",sheet_name: 'Test_Sheet', bootstrap: false, exportButtons: false});
        const exportData = exportTable.getExportData();
        if (!xlsxData){
            xlsxData = exportData[table.id].xlsx;
        }
        tablesData.push(exportData[table.id].xlsx.data);
        if (sheetPrefix) {
            const sheetName = sheetPrefix.replaceAll("{id}", table.id);
            sheetNames.push(sheetName)
        }
    });
    const fileExtension = xlsxData.fileExtension;
    const mimeType = xlsxData.mimeType;
    const fileName = `${filePrefix}_${getCurrentTimestamp()}`;
    const defaultExportTable = new TableExport(tables[0], {formats:['xlsx'],filename: "test_export",sheet_name: 'Test_Sheet', bootstrap: false, exportButtons: false});
    exportMultiSheet(defaultExportTable, tablesData, mimeType, fileName, sheetNames, fileExtension)
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
       await addNewCID(cid, skin);
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
       const promptModeButton = document.getElementById(`prompt-mode-${conversationData['_id']}`);

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
       await addRecorder(conversationData);


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
           const selectedTables = messageListContainer.getElementsByClassName('selected');
           exportTablesToExcel(selectedTables, `prompts_of_${cid}`, 'prompt_{id}');
           Array.from(selectedTables).forEach(selectedTable => {
               selectedTable.classList.remove('selected');
           })
       });
    }

    if (chatCloseButton.hasAttribute('data-target-cid')) {
       chatCloseButton.addEventListener('click', async (e) => {
           conversationHolder.removeChild(conversationParent);
           await removeConversation(cid);
           clearStateCache(cid);
       });
    }
    setTimeout(() => getMessageListContainer(conversationData['_id']).lastElementChild?.scrollIntoView(true), 0);
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
            }).catch(async err=> {
                console.warn('Failed to fulfill request due to error:',err);
                if (input === '1'){
                    await createNewConversation('Global', false, '1');
                }
            });
    }
    return conversationData;
}


/**
 * Returns table representing chat alignment
 * @return {Table}
 */
const getChatAlignmentDb = () => {
    return getDb(DATABASES.CHATS, DB_TABLES.CHAT_ALIGNMENT);
}
/**
 * Retrieves conversation layout from local storage
 * @returns {Array} collection of database-stored elements
 */
async function retrieveItemsLayout(idOnly=false){
    let layout = await getChatAlignmentDb().orderBy("added_on").toArray();
    if (idOnly){
        layout = layout.map(a => a.cid);
    }
    return layout;
}

/**
 * Adds new conversation id to local storage
 * @param cid: conversation id to add
 * @param skin: conversation skin to add
 */
async function addNewCID(cid, skin){
    return await getChatAlignmentDb().put({'cid': cid, 'skin': skin, 'added_on': getCurrentTimestamp()}, [cid]);
}

/**
 * Removed conversation id from local storage
 * @param cid: conversation id to remove
 */
async function removeConversation(cid){
    return await getChatAlignmentDb().where({cid: cid}).delete();
}

/**
 * Checks if conversation is displayed
 * @param cid: target conversation id
 * @return true if cid is stored in client db, false otherwise
 */
async function isDisplayed(cid){
    return await getStoredConversationData(cid) !== undefined;
}


/**
 * Gets value of desired property in stored conversation
 * @param cid: target conversation id
 * @return true if cid is displayed, false otherwise
 */
async function getStoredConversationData(cid){
    return await getChatAlignmentDb().where( {cid: cid} ).first();
}

/**
 * Returns current skin of provided conversation id
 * @param cid: target conversation id
 * @return {string} skin from CONVERSATION_SKINS
 */
async function getCurrentSkin(cid){
    const storedCID = await getStoredConversationData(cid);
    if(storedCID) {
        return storedCID['skin'];
    }return null;
}

/**
 * Sets new skin value to the selected conversation
 * @param cid: target conversation id
 * @param property: key of stored conversation
 * @param value: value to set
 */
function updateCIDStoreProperty(cid, property, value){
    const updateObj = {}
    updateObj[property] = value;
    return getChatAlignmentDb().update(cid, updateObj);
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
    let cachedItems = await retrieveItemsLayout();
    if (cachedItems.length === 0){
        cachedItems = [{'cid': '1', 'added_on': getCurrentTimestamp(), 'skin': CONVERSATION_SKINS.BASE}]
        await addNewCID('1', CONVERSATION_SKINS.BASE);
    }
    for (const item of cachedItems) {
        await getConversationDataByInput(item.cid, item.skin).then(async conversationData=>{
            if(conversationData && Object.keys(conversationData).length > 0) {
                await buildConversation(conversationData, item.skin, false);
            }else{
                if (item.cid !== '1') {
                    displayAlert(document.getElementById('conversationsBody'), 'No matching conversation found', 'danger', 'noRestoreConversationAlert', {'type': alertBehaviors.AUTO_EXPIRE});
                }
                await removeConversation(item.cid);
            }
        });
    }
    console.log('Chat Alignment Restored');
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
    const messageContainer = getMessageListContainer(cid);
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
    Array.from(conversationBody.getElementsByClassName('conversationContainer')).forEach(async conversation=>{
        const cid = conversation.getElementsByClassName('card')[0].id;
        const skin = await getCurrentSkin(cid);
        if (skin === CONVERSATION_SKINS.BASE) {
            const messages = getMessagesOfCID(cid);
            Array.from(messages).forEach(message => {
                if (message.hasAttribute('data-sender')) {
                    const messageSenderNickname = message.getAttribute('data-sender');
                    if (message.parentElement.parentElement.className !== 'announcement')
                        message.parentElement.parentElement.className = (currentUser && messageSenderNickname === currentUser['nickname'])?'in':'out';
                }
            });
        }
        await initLanguageSelectors(cid);
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

/**
 * Enum of possible displayed chat states
 * "active" - ready to be used by user
 * "updating" - in processes of applying changes, temporary unavailable
 */
const CHAT_STATES = {
    ACTIVE: 'active',
    UPDATING: 'updating',
}

/**
 * Sets state to the desired cid
 * @param cid: desired conversation id
 * @param state: desired state
 * @param state_msg: message following state transition (e.g. why chat is updating)
 */
function setChatState(cid, state='active', state_msg = ''){
    // TODO: refactor this method to handle when there are multiple messages on a stack
    console.log(`cid=${cid}, state=${state}, state_msg=${state_msg}`)
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
            if (await isDisplayed(conversationData['_id'])) {
                displayAlert(alertParent, 'Chat is already displayed', 'danger');
            } else if (conversationData && Object.keys(conversationData).length > 0) {
                await buildConversation(conversationData, skin);
                for (const inputType of ['incoming', 'outcoming']){
                    await requestTranslation(conversationData['_id'], null, null, inputType);
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
    formData.append('id', conversationID);
    formData.append('is_private', isPrivate)

    await fetchServer(`chat_api/new`,  REQUEST_METHODS.POST, formData).then(async response => {
        const responseJson = await response.json();
        let responseOk = false;
        if (response.ok) {
            await buildConversation(responseJson).then(async cid=>{
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
        await restoreChatAlignment()
            .then(async _=>await refreshCurrentUser(true))
            .then(async _=> await requestChatsLanguageRefresh());
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
        conversationSearchInput.addEventListener('input', async (e)=>{ await renderSuggestions();});
        conversationSearchInput.addEventListener('propertychange', async (e)=>{ await renderSuggestions();});
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
