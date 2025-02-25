const importConversationModal = $('#importConversationModal');
const importConversationOpener = document.getElementById('importConversationOpener');
const conversationSearchInput = document.getElementById('conversationSearchInput');
const importConversationModalSuggestions = document.getElementById('importConversationModalSuggestions');

const addBySearch = document.getElementById('addBySearch');

const newConversationModal = $('#newConversationModal');
const bindServiceSelect = document.getElementById('bind-service-select')
const addNewConversation = document.getElementById('addNewConversation');

const conversationBody = document.getElementById('conversationsBody');

let conversationState = {};

/**
 * Clears conversation state cache
 * @param cid - Conversation ID to clear
 */
const clearStateCache = (cid) => {
    delete conversationState[cid];
}
/**
 * Sets all participants counters to zero
 */
const setAllCountersToZero = () => {
    const countNodes = document.querySelectorAll('[id^="participants-count-"]');
    countNodes.forEach(node => node.innerText = 0);
}


/**
 * Sets participants count for conversation view
 * @param cid - desired conversation id
 */
const refreshSubmindsCount = (cid) => {
    const participantsCountNode = document.getElementById(`participants-count-${cid}`);
    if (participantsCountNode){
        let submindsCount = 0
        if (!isEmpty(submindsState)){
            submindsCount = submindsState["subminds_per_cid"][cid].filter(submind => {
                const connectedSubmind = submindsState.connected_subminds[submind.submind_id];
                return connectedSubmind && connectedSubmind.bot_type === "submind" && submind.status === "active";
            }).length;
        }
        participantsCountNode.innerText = submindsCount;
    }
}


/**
 * Saves attached files to the server
 * @param cid - target conversation id
 * @return attachments array or `-1` if something went wrong
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
        setChatState(cid, 'active')
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
 * Initiates selection of the table rows.
 * @param table - target table to select
 * @param exportToExcelBtn - DOM element of `Export to Excel` button
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
 * @param table - HTMLTable element
 * @param exportToExcelBtn - export to excel button (optional)
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
 * Wraps the provided array of HTMLTable elements into XLSX file and exports it to the invoked user
 * @param tables - array of HTMLTable elements to export
 * @param filePrefix - prefix of the file name to be imported
 * @param sheetPrefix - prefix to apply for each sheet generated per HTMLTable
 * @param appname - name of the application to export (defaults to Excel)
 */
const exportTablesToExcel = (function() {
    const uri = 'data:application/vnd.ms-excel;base64,';
    const tmplWorkbookXML = `
        <?xml version="1.0"?>
        <?mso-application progid="Excel.Sheet"?>
        <Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
            <DocumentProperties xmlns="urn:schemas-microsoft-com:office:office">
                <Author>PyKlatchat Generator</Author>
                <Created>{created}</Created>
            </DocumentProperties>
          <Styles>
              <Style ss:ID="Currency"><NumberFormat ss:Format="Currency"></NumberFormat></Style>'
              <Style ss:ID="Date"><NumberFormat ss:Format="Medium Date"></NumberFormat></Style>'
          </Styles>
          {worksheets}
        </Workbook>
    `
    const tmplWorksheetXML = '<Worksheet ss:Name="{nameWS}"><Table>{rows}</Table></Worksheet>'
    const tmplCellXML = '<Cell><Data ss:Type="String">{data}</Data></Cell>'
    const base64 = function(s) { return window.btoa(unescape(encodeURIComponent(s))) }
    const format = function(s, c) { return s.replace(/{(\w+)}/g, function(m, p) { return c[p]; }) }
    return function(tables, filePrefix, sheetPrefix='', appname='Excel') {
      let ctx = "";
      let workbookXML = "";
      let worksheetsXML = "";
      let rowsXML = "";

      for (let i = 0; i < tables.length; i++) {
        if (!tables[i].nodeType) tables[i] = document.getElementById(tables[i]);
        for (let j = 0; j < tables[i].rows.length; j++) {
          rowsXML += '<Row>'
          for (let k = 0; k < tables[i].rows[j].cells.length; k++) {
            let data = tables[i].rows[j].cells[k].innerHTML
            if (k === 0){
                const chatImgElem = tables[i].rows[j].cells[k].getElementsByClassName("chat-img")[0]
                if (chatImgElem){
                    data = chatImgElem.getAttribute("title");
                }
            }
            ctx = {
                data: data,
            };
            rowsXML += format(tmplCellXML, ctx);
          }
          rowsXML += '</Row>'
        }
        const sheetName = sheetPrefix.replaceAll("{id}", tables[i].id);
        ctx = {rows: rowsXML, nameWS: sheetName || 'Sheet' + i};
        worksheetsXML += format(tmplWorksheetXML, ctx);
        rowsXML = "";
      }

      ctx = {created: getCurrentTimestamp()*1000, worksheets: worksheetsXML};
      workbookXML = format(tmplWorkbookXML, ctx);

      let link = document.createElement("A");
      link.href = uri + base64(workbookXML);
      const fileName = `${filePrefix}_${getCurrentTimestamp()}`;
      link.download = `${fileName}.xls`;
      link.target = '_blank';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  })();


/**
 * Sends the message based on input
 * @param inputElem - input DOM element
 * @param cid - target conversation id
 * @param repliedMessageId - replied message id (optional)
 * @param isAudio - `1` if the message is audio-message (defaults to `0`)
 * @param isAnnouncement - `1` if the message is an announcement (defaults to `0`)
 */
const sendMessage = async (inputElem, cid, repliedMessageId=null, isAudio='0', isAnnouncement='0') => {
    const attachments = await saveAttachedFiles(cid);
    if (Array.isArray(attachments)) {
       emitUserMessage(inputElem, cid, repliedMessageId, attachments, isAudio, isAnnouncement);
    }
    inputElem.value = "";
}

/**
 * Gets all opened chat ids
 * @return {[]} list of displayed chat ids
 */
function getOpenedChatIds(){
    let cids = [];
    Array.from(conversationBody.getElementsByClassName('conversationContainer')).forEach(conversationContainer=>{
        cids.push(conversationContainer.getElementsByClassName('card')[0].id);
    });
    return cids;
}

const resizeConversationContainers = () => {
    const openedChatIds = getOpenedChatIds();
    const newWidth = `${100/openedChatIds.length}vw`;
    openedChatIds.forEach(cid => {
        document.getElementById(cid).style.width = newWidth;
    })
}

/**
 * Builds new conversation HTML from provided data and attaches it to the list of displayed conversations
 * @param conversationData - JS Object containing conversation data of type:
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
 * @param skin - Conversation skin to build
 * @param remember - to store this conversation into localStorage (defaults to true)*
 * @param conversationParentID - ID of conversation parent
 * @return id of the built conversation
 */
async function buildConversation(conversationData, skin, remember=true,conversationParentID = 'conversationsBody'){
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

    resizeConversationContainers()

    setChatState(cid, CHAT_STATES.UPDATING, "Loading messages...")
    initMessages(conversationData, skin).then(_ => setChatState(cid, CHAT_STATES.ACTIVE));

    const messageListContainer = getMessageListContainer(cid);
    const currentConversation = document.getElementById(cid);
    const conversationParent = currentConversation.parentElement;
    const conversationHolder = conversationParent.parentElement;

    let chatCloseButton = document.getElementById(`close-${cid}`);
    const chatInputButton = document.getElementById(conversationData['_id'] + '-send');
    const filenamesContainer = document.getElementById(`filename-container-${conversationData['_id']}`)
    const attachmentsButton = document.getElementById('file-input-' + conversationData['_id']);
    const textInputElem = document.getElementById(conversationData['_id'] + '-input');
    if (chatInputButton.hasAttribute('data-target-cid')) {
       textInputElem.addEventListener('keyup', async (e)=>{
           if (e.key === 'Enter' && !e.shiftKey){
              await sendMessage(textInputElem, conversationData['_id']);
           }
       });
       chatInputButton.addEventListener('click', async (e) => {
           await sendMessage(textInputElem, conversationData['_id']);
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
    await addRecorder(conversationData);
    await initLanguageSelectors(conversationData['_id']);

    if (skin === CONVERSATION_SKINS.BASE) {
       const promptModeButton = document.getElementById(`prompt-mode-${conversationData['_id']}`);

       promptModeButton.addEventListener('click', async (e) => {
           e.preventDefault();
           chatCloseButton.click();
           await displayConversation(conversationData['_id'], CONVERSATION_SKINS.PROMPTS, null, conversationParentID);
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
           await displayConversation(cid, CONVERSATION_SKINS.BASE, null, conversationParentID);
       });

       // TODO: make an array of prompt tables only in dedicated conversation
       Array.from(getMessagesOfCID(cid, MESSAGE_REFER_TYPE.ALL, 'prompt', false)).forEach(table => {

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
           });
       });
    }

    if (chatCloseButton.hasAttribute('data-target-cid')) {
       chatCloseButton.addEventListener('click', async (_) => {
           conversationHolder.removeChild(conversationParent);
           await removeConversation(cid);
           clearStateCache(cid);
           resizeConversationContainers()
       });
    }
    // Hide close button for Nano Frames
    if (configData.client === CLIENTS.NANO){
        chatCloseButton.hidden = true;
    }
    document.getElementById('klatchatHeader').scrollIntoView(true);
    scrollChatToLastMessage(cid);
    return cid;
}

/**
 * Gets conversation data based on input string
 * @param input - input string text
 * @param oldestMessageTS - creation timestamp of the oldest displayed message
 * @param skin - resolves by server for which data to return
 * @param maxResults - max number of messages to fetch
 * @returns {Promise<{}>} promise resolving conversation data returned
 */
async function getConversationDataByInput(input, skin, oldestMessageTS=null, maxResults=10){
    let conversationData = {};
    if(input){
        let query_url = `chat_api/search/${input.toString()}?limit_chat_history=${maxResults}&skin=${skin}`;
        if(oldestMessageTS){
            query_url += `&creation_time_from=${oldestMessageTS}`;
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
                if (getUserMessages(data, null).length === 0){
                    console.log('All of the messages are already displayed');
                    setDefault(setDefault(conversationState, data['_id'], {}), 'all_messages_displayed', true);
                }
                conversationData = data;
            }).catch(async err=> {
                console.warn('Failed to fulfill request due to error:',err);
            });
    }
    return conversationData;
}

/**
 * Returns table representing chat alignment
 * @return {Table}
 */
const getChatAlignmentTable = () => {
    return getDb(DATABASES.CHATS, DB_TABLES.CHAT_ALIGNMENT);
}

/**
 * Retrieves conversation layout from local storage
 * @returns {Array} collection of database-stored elements
 */
async function retrieveItemsLayout(idOnly=false){
    let layout = await getChatAlignmentTable().orderBy("added_on").toArray();
    if (idOnly){
        layout = layout.map(a => a.cid);
    }
    return layout;
}


/**
 * Adds new conversation id to local storage
 * @param cid - conversation id to add
 * @param skin - conversation skin to add
 */
async function addNewCID(cid, skin){
    return await getChatAlignmentTable().put({'cid': cid, 'skin': skin, 'added_on': getCurrentTimestamp()}, [cid]);
}

/**
 * Removed conversation id from local storage
 * @param cid - conversation id to remove
 */
async function removeConversation(cid){
    return await Promise.all([DBGateway.getInstance(DB_TABLES.CHAT_ALIGNMENT).deleteItem(cid),
                                     DBGateway.getInstance(DB_TABLES.CHAT_MESSAGES_PAGINATION).deleteItem(cid)]);
}

/**
 * Checks if conversation is displayed
 * @param cid - target conversation id
 *
 * @return true if cid is stored in client db, false otherwise
 */
function isDisplayed(cid) {
    return document.getElementById(cid) !== null;
}


/**
 * Gets value of desired property in stored conversation
 * @param cid - target conversation id
 *
 * @return true if cid is displayed, false otherwise
 */
async function getStoredConversationData(cid){
    return await getChatAlignmentTable().where( {cid: cid} ).first();
}

/**
 * Returns current skin of provided conversation id
 * @param cid - target conversation id
 *
 * @return {string} skin from CONVERSATION_SKINS
 */
async function getCurrentSkin(cid){
    const storedCID = await getStoredConversationData(cid);
    if(storedCID) {
        return storedCID['skin'];
    }return null;
}

/**
 * Boolean function that checks whether live chats must be displayed based on page meta properties
 * @returns {boolean} true if live chat should be displayed, false otherwise
 */
const shouldDisplayLiveChat = () => {
    const liveMetaElem = document.querySelector("meta[name='live']");
    if (liveMetaElem){
        return liveMetaElem.getAttribute("content") === "1"
    }
    return false
}

/**
 * Fetches latest live conversation from the klat server API and builds its HTML
 * @returns {Promise<*>} fetched conversation data
 */
const displayLiveChat = async () => {
    return await fetchServer('chat_api/live')
        .then(response => {
            if(response.ok){
                return response.json();
            }else{
                throw response.statusText;
            }
        })
        .then(data => {
            if (getUserMessages(data, null).length === 0){
                console.debug('All of the messages are already displayed');
                setDefault(setDefault(conversationState, data['_id'], {}), 'all_messages_displayed', true);
            }
            return data;
        })
        .then(
            async data => {
                await buildConversation(data, CONVERSATION_SKINS.PROMPTS, true);
                return data;
            }
        )
        .catch(async err=> {
            console.warn('Failed to display live chat:',err);
        });
}

/**
 * Restores chat alignment based on the page cache
 */
const restoreChatAlignmentFromCache = async () => {
    let cachedItems = await retrieveItemsLayout();
    if (cachedItems.length === 0) {
        await displayLiveChat();
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
}

/**
 * Custom Event fired on supported languages init
 * @type {CustomEvent<string>}
 */
const chatAlignmentRestoredEvent = new CustomEvent("chatAlignmentRestored", { "detail": "Event that is fired when chat alignment is restored" });

/**
 * Restores chats alignment from the local storage
**/
async function restoreChatAlignment(){
    if (shouldDisplayLiveChat()){
        await displayLiveChat();
    } else {
        await restoreChatAlignmentFromCache();
    }
    console.debug('Chat Alignment Restored');
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
 * @param cid - target conversation id
 * @param messageReferType - message refer type to consider from `MESSAGE_REFER_TYPE`
 * @param idOnly - to return id only (defaults to false)
 * @param forceType - to get only the certain type of messages (optional)
 *
 * @return array of message DOM objects under given conversation
 */
function getMessagesOfCID(cid, messageReferType=MESSAGE_REFER_TYPE.ALL, forceType=null, idOnly=false){
    let messages = []
    const messageContainer = getMessageListContainer(cid);
    if(messageContainer){
        const listItems = messageContainer.getElementsByTagName('li');
        Array.from(listItems).forEach(li=>{
           try {
               const messageNode = getMessageNode(li, forceType);
               if (messageNode) {
                   if (messageReferType === MESSAGE_REFER_TYPE.ALL ||
                       (messageReferType === MESSAGE_REFER_TYPE.MINE && messageNode.getAttribute( 'data-sender' ) === currentUser['nickname']) ||
                       (messageReferType === MESSAGE_REFER_TYPE.OTHERS && messageNode.getAttribute( 'data-sender' ) !== currentUser['nickname'])) {
                       if (idOnly) {
                           messages.push( messageNode.id );
                       } else {
                           messages.push( messageNode );
                       }
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
 * Refreshes chat view (for instance when user session gets updated)
 */
function refreshChatView(conversationContainer=null){
    if (!conversationContainer){
        conversationContainer = conversationBody;
    }
    Array.from(conversationContainer.getElementsByClassName('conversationContainer')).forEach(async conversation=>{
        const cid = conversation.getElementsByClassName('card')[0].id;
        const skin = await getCurrentSkin(cid);
        if (skin === CONVERSATION_SKINS.BASE) {
            const messages = getMessagesOfCID(cid, MESSAGE_REFER_TYPE.ALL, 'plain');
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
 * @param cid - target conversation id
 * @param state - the new chat state from `CHAT_STATES`
 * @param state_msg - reason for state transitioning (optional)
 */
function setChatState(cid, state=CHAT_STATES.ACTIVE, state_msg = ''){
    // TODO: refactor this method to handle when there are multiple messages on a stack
    // console.log(`cid=${cid}, state=${state}, state_msg=${state_msg}`)
    const cidNode = document.getElementById(cid);
    if (cidNode) {
        setDefault(setDefault(conversationState, cid, {}))
        const spinner = document.getElementById( `${cid}-spinner` );
        const spinnerUpdateMsg = document.getElementById( `${cid}-update-msg` );
        if (state === 'updating') {
            cidNode.classList.add( 'chat-loading' );
            spinner.style.setProperty( 'display', 'flex', 'important' );
            spinnerUpdateMsg.innerHTML = state_msg;
        } else if (state === 'active') {
            cidNode.classList.remove( 'chat-loading' );
            spinner.style.setProperty( 'display', 'none', 'important' );
            spinnerUpdateMsg.innerHTML = '';
        }
        conversationState[cid]['state'] = state;
        conversationState[cid]['state_message'] = state_msg;
    }
}

/**
 * Displays first conversation matching search string
 * @param searchStr - Search string to find matching conversation
 * @param skin - target conversation skin to display
 * @param alertParentID - id of the element to display alert in
 * @param conversationParentID - parent Node ID of the conversation
 */
async function displayConversation(searchStr, skin=CONVERSATION_SKINS.PROMPTS, alertParentID = null, conversationParentID='conversationsBody'){
    if (getOpenedChatIds().length === configData.MAX_CONVERSATIONS_PER_PAGE){
        alert(`Up to ${configData.MAX_CONVERSATIONS_PER_PAGE} allowed per page`)
    }
    else if (searchStr !== "") {
        const alertParent = document.getElementById(alertParentID || conversationParentID);
        await getConversationDataByInput(searchStr, skin, null, 10).then(async conversationData => {
            let responseOk = false;
            if (!conversationData || Object.keys(conversationData).length === 0){
                displayAlert(
                    alertParent,
                    'Cannot find conversation matching your search',
                    'danger',
                    'noSuchConversationAlert',
                    {'type': alertBehaviors.AUTO_EXPIRE}
                    );
            }
            else if (isDisplayed(conversationData['_id'])) {
                displayAlert(alertParent, 'Chat is already displayed', 'danger');
            } else {
                await buildConversation(conversationData, skin, true, conversationParentID);
                if (skin === CONVERSATION_SKINS.BASE) {
                    for (const inputType of ['incoming', 'outcoming']) {
                        await requestTranslation( conversationData['_id'], null, null, inputType );
                    }
                }
                responseOk = true;
                if (configData.client === CLIENTS.NANO) {
                    attachEditModalInvoker(document.getElementById(`${conversationData['_id']}-account-link`));
                    updateNavbar();
                    initSettings(document.getElementById(`${conversationData['_id']}-settings-link`));
                }
            }
            return responseOk;
        });
    }
}

/**
 * Handles requests on creation new conversation by the user
 * @param conversationName - New Conversation Name
 * @param isPrivate - if conversation should be private (defaults to false)
 * @param boundServiceID - id of the service to bind to conversation (optional)
 * @param createLiveConversation - if conversation should be treated as live conversation (defaults to false)
 */
async function createNewConversation(conversationName, isPrivate=false,boundServiceID=null, createLiveConversation=false) {

    let formData = new FormData();

    formData.append('conversation_name', conversationName);
    formData.append('is_private', isPrivate? '1': '0')
    formData.append('bound_service', boundServiceID?boundServiceID: '');
    formData.append('is_live_conversation', createLiveConversation? '1': '0')

    return await fetchServer(`chat_api/new`,  REQUEST_METHODS.POST, formData)
        .then(async response => {
            const responseJson = await response.json();
            let responseOk = false;
            if (response.ok) {
                await buildConversation(responseJson, CONVERSATION_SKINS.PROMPTS);
                responseOk = true;
            } else {
                displayAlert('newConversationModalBody',
                    `${responseJson['msg']}`,
                    'danger');
            }
            return responseOk;
        });
}

document.addEventListener('DOMContentLoaded', (_)=>{

    if (configData['client'] === CLIENTS.MAIN) {
        document.addEventListener('supportedLanguagesLoaded', async (_)=>{
            await refreshCurrentUser(false)
            .then(async _ => await restoreChatAlignment())
            .then(async _=>await refreshCurrentUser(true))
            .then(async _=> await requestChatsLanguageRefresh());
        });
        addBySearch.addEventListener('click', async (e) => {
            e.preventDefault();
            displayConversation(conversationSearchInput.value, CONVERSATION_SKINS.PROMPTS, 'importConversationModalBody').then(responseOk=> {
                conversationSearchInput.value = "";
                if(responseOk) {
                    importConversationModal.modal('hide');
                }
            });
        });
        conversationSearchInput.addEventListener('input', async (_)=>{ await renderSuggestions();});
        addNewConversation.addEventListener('click', async (e) => {
            e.preventDefault();
            const newConversationName = document.getElementById('conversationName');
            const isPrivate = document.getElementById('isPrivate');
            const createLiveConversation = document.getElementById("createLiveConversation");
            let boundServiceID = bindServiceSelect.value;

            if (boundServiceID){
                const targetItem = document.getElementById(boundServiceID);
                if (targetItem.value) {
                    if (targetItem.nodeName === 'SELECT') {
                        boundServiceID = targetItem.value;
                    } else {
                        boundServiceID = targetItem.getAttribute( 'data-value' ) + '.' + targetItem.value
                    }
                }else{
                    displayAlert('newConversationModalBody', 'Missing bound service name');
                    return -1;
                }
            }

            createNewConversation(newConversationName.value, isPrivate.checked, boundServiceID, createLiveConversation.checked).then(responseOk=>{
                newConversationName.value = "";
                isPrivate.checked = false;
                if(responseOk) {
                    newConversationModal.modal('hide');
                }
            });
        });
        importConversationOpener.addEventListener('click', async (e)=>{
            e.preventDefault();
            conversationSearchInput.value = "";
            await renderSuggestions();
        });
        bindServiceSelect.addEventListener("change", function() {
            Array.from(document.getElementsByClassName('create-conversation-bind-group')).forEach(x=>{
                x.hidden = true;
            });
            if(bindServiceSelect.value) {
                const targetItem = document.getElementById(bindServiceSelect.value);
                targetItem.hidden = false;
            }
        });
    }
});
