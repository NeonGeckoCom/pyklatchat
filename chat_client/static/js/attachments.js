let __inputFileList = {};

/**
 * Gets uploaded files from specified conversation id
 * @param cid specified conversation id
 * @return {*} list of files from specified cid if any
 */
function getUploadedFiles(cid){
    if(__inputFileList.hasOwnProperty(cid)){
        return __inputFileList[cid];
    }return [];
}

/**
 * Cleans uploaded files per conversation
 */
function cleanUploadedFiles(cid){
    if(__inputFileList.hasOwnProperty(cid)) {
        delete __inputFileList[cid];
    }
    const attachmentsButton = document.getElementById('file-input-'+cid);
    attachmentsButton.value = "";
    const fileContainer = document.getElementById('filename-container-'+cid);
    fileContainer.innerHTML = "";
}

/**
 * Adds File upload to specified cid
 * @param cid: mentioned cid
 * @param file: File object
 */
function addUpload(cid, file){
    if(!__inputFileList.hasOwnProperty(cid)){
        __inputFileList[cid] = [];
    }
    __inputFileList[cid].push(file);
}

/**
 * Adds download request on attachment item click
 * @param attachmentItem: desired attachment item
 * @param cid: current conversation id
 * @param messageID: current message id
 */
async function downloadAttachment(attachmentItem, cid, messageID){
    if(attachmentItem){
        const fileName = attachmentItem.getAttribute('data-file-name');
        const mime = attachmentItem.getAttribute('data-mime');
        const getFileURL = `files/${messageID}/get_attachment/${fileName}`;
        await fetchServer(getFileURL).then(async response => {
            response.ok ?
                download(await response.blob(), fileName, mime)
                :console.error(`No file data received for path, 
                                  cid=${cid};\n
                                  message_id=${messageID};\n
                                  file_name=${fileName}`)
        }).catch(err=>console.error(`Failed to fetch: ${getFileURL}: ${err}`));
    }
}

/**
 * Attaches message replies to initialized conversation
 * @param conversationData: conversation data object
 */
function addAttachments(conversationData){
    if(conversationData.hasOwnProperty('chat_flow')) {
        getUserMessages(conversationData).forEach(message => {
            resolveMessageAttachments(conversationData['_id'], message['message_id'], message?.attachments);
        });
    }
}

/**
 * Activates attachments event listeners for message attachments in specified conversation
 * @param cid: desired conversation id
 * @param elem: parent element for attachment (defaults to document)
 */
function activateAttachments(cid, elem=null){
    if (!elem){
        elem = document;
    }
    Array.from(elem.getElementsByClassName('attachment-item')).forEach(attachmentItem=>{
        attachmentItem.addEventListener('click', async (e)=>{
           e.preventDefault();
           const attachmentName = attachmentItem.getAttribute('data-file-name');
           try {
               setChatState(cid, 'updating', `Downloading attachment file`);
               await downloadAttachment(attachmentItem, cid, attachmentItem.parentNode.parentNode.id);
           } catch (e) {
               console.warn(`Failed to download attachment file - ${attachmentName} (${e})`)
           } finally {
               setChatState(cid, 'active');
           }
        });
    });
}


/**
 * Returns DOM element to include as file resolver based on its name
 * @param filename: name of file to fetch
 * @return {string}: resulting DOM element
 */
function attachmentHTMLBasedOnFilename(filename){

    let fSplitted = filename.split('.');
    if (fSplitted.length > 1){
        const extension = fSplitted.pop();
        const shrinkedName = shrinkToFit(filename, 12, `...${extension}`);
        if (IMAGE_EXTENSIONS.includes(extension)){
            return `<i class="fa fa-file-image"></i> ${shrinkedName}`;
        }else{
            return shrinkedName;
        }
    }return shrinkToFit(filename, 12);
}

/**
 * Resolves attachments to the message
 * @param cid: id of conversation
 * @param messageID: id of user message
 * @param attachments list of attachments received
 */
function resolveMessageAttachments(cid, messageID,attachments = []){
    if(messageID) {
        const messageElem = document.getElementById(messageID);
        if(messageElem) {
            const attachmentToggle = messageElem.getElementsByClassName('attachment-toggle')[0];
            if (attachments.length > 0) {
                if (messageElem) {
                    const attachmentPlaceholder = messageElem.getElementsByClassName('attachments-placeholder')[0];
                    attachments.forEach(attachment => {
                        const attachmentHTML = `<span class="attachment-item" data-file-name="${attachment['name']}" data-mime="${attachment['mime']}" data-size="${attachment['size']}">
                                            ${attachmentHTMLBasedOnFilename(attachment['name'])}
                                        </span><br>`;
                        attachmentPlaceholder.insertAdjacentHTML('afterbegin', attachmentHTML);
                    });
                    attachmentToggle.addEventListener('click', (e) => {
                        attachmentPlaceholder.style.display = attachmentPlaceholder.style.display === "none" ? "" : "none";
                    });
                    activateAttachments(cid, attachmentPlaceholder);
                    attachmentToggle.style.display = "";
                    // attachmentPlaceholder.style.display = "";
                }
            } else {
                attachmentToggle.style.display = "none";
            }
        }
    }
}