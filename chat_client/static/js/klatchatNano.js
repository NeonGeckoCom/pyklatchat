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
}/**
* Enum of possible Alert Behaviours:
* - DEFAULT: static alert message appeared with no expiration time
* - AUTO_EXPIRE: alert message will be expired after some amount of time (defaults to 3 seconds)
*/
const alertBehaviors = {
STATIC: 'static',
AUTO_EXPIRE: 'auto_expire'
}

/**
* Adds Bootstrap alert HTML to specified element's id
* @param parentElem: DOM Element in which to display alert
* @param text: Text of alert (defaults 'Error Occurred')
* @param alertType: Type of alert from bootstrap-supported alert types (defaults to 'danger')
* @param alertID: Id of alert to display (defaults to 'alert')
* @param alertBehaviorProperties: optional properties associated with alert message behavior
*/
function displayAlert(parentElem,text='Error Occurred',alertType='danger',alertID='alert',
alertBehaviorProperties=null){
if (!parentElem){
console.warn('Alert is not displayed as parentElem is not defined');
return
}
if(!['info','success','warning','danger','primary','secondary','dark'].includes(alertType)){
alertType = 'danger'; //default
}
let alert = document.getElementById(alertID);
if(alert){
alert.remove();
}

if(text) {
parentElem.insertAdjacentHTML('afterbegin',
`<div class="alert alert-${alertType} alert-dismissible" role="alert" id="${alertID}">
<b>${text}</b>
<button type="button" class="close" data-dismiss="alert" aria-label="Close">
<span aria-hidden="true">&times;</span>
</button>
</div>`);
if (alertBehaviorProperties){
setDefault(alertBehaviorProperties, 'type', alertBehaviors.STATIC);
if (alertBehaviorProperties['type'] === alertBehaviors.AUTO_EXPIRE){
const expirationTime = setDefault(alertBehaviorProperties, 'expiration', 3000);
const slideLength = setDefault(alertBehaviorProperties, 'fadeLength', 500);
setTimeout(function() {
$(`#${alertID}`).slideUp(slideLength, () => {
$(this).remove();
});
}, expirationTime);
}
}
}
}

/**
* Generates UUID hex
* @param length: length of UUID (defaults to 8)
* @param strPattern: pattern to follow for UUID (optional)
* @returns {string} Generated UUID hex
*/
function generateUUID(length=8, strPattern='00-0-4-1-000') {
const a = crypto.getRandomValues(new Uint16Array(length));
let i = 0;
return strPattern.replace(/[^-]/g,
s => (a[i++] + s * 0x10000 >> s).toString(16).padStart(4, '0')
);
}

/**
* Shrinks text to fit into desired length
* @param text: Text to shrink
* @param maxLength: max length of text to save
* @param suffix: suffix to apply after shrunk string
* @returns {string} Shrunk text, fitting into "maxLength"
*/
function shrinkToFit(text, maxLength, suffix='...'){
if(text.length>maxLength){
text = text.substring(0, maxLength) + suffix;
}return text;
}


/**
* Converts file to base64
* @param file: desired file
* @return {Promise}
*/
const toBase64 = file => new Promise((resolve, reject) => {
const reader = new FileReader();
reader.readAsDataURL(file);
reader.onload = () => resolve(reader.result);
reader.onerror = error => reject(error);
});

/**
* Extracts filename from path
* @param path: path to extract from
*/
function getFilenameFromPath(path){
return path.replace(/.*[\/\\]/, '');
}

/**
* Fetches URL with no-cors mode
* @param url: URL to fetch
* @param properties: request properties
* @return {Promise<Response>}: Promise of fetching
*/
function fetchNoCors(url, properties = {}){
properties['mode'] = 'no-cors';
return fetch(url, properties)
}

/**
* Checks if element is in current viewport
* @param element: DOM element to check
* @return {boolean} True if element in current viewport False otherwise
*/
function isInViewport(element) {
const rect = element.getBoundingClientRect();
return (
rect.top >= 0 &&
rect.left >= 0 &&
rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
rect.right <= (window.innerWidth || document.documentElement.clientWidth)
);
}

/**
* Sets default value to the object under the specified key
* @param obj: object to consider
* @param key: object key to set
* @param val: default value to set
*/
function setDefault(obj, key, val){
if(obj){
obj[key] ??= val;
}
return obj[key];
}

/**
* Deletes provided element from DOM
* @param elem: DOM Object to delete
*/
function deleteElement(elem){
if (elem && elem?.parentElement) return elem.parentElement.removeChild(elem);
}

const MIMES = [
["xml","application/xml"],
["bin","application/vnd.ms-excel.sheet.binary.macroEnabled.main"],
["vml","application/vnd.openxmlformats-officedocument.vmlDrawing"],
["data","application/vnd.openxmlformats-officedocument.model+data"],
["bmp","image/bmp"],["png","image/png"],
["gif","image/gif"],["emf","image/x-emf"],
["wmf","image/x-wmf"],["jpg","image/jpeg"],
["jpeg","image/jpeg"],["tif","image/tiff"],
["tiff","image/tiff"], ["jfif","image/jfif"],["pdf","application/pdf"],
["rels","application/vnd.openxmlformats-package.relationships+xml"]];

const IMAGE_EXTENSIONS = MIMES.filter(item => item[1].startsWith('image/')).map(item=>item[0]);/**
* Object representing loaded HTML components mapping:
* - key: component name,
* - value: HTML template that should be populated with actual data)
* @type Object
*/
let loadedComponents = {}

/**
* Fetches template context into provided html template
* @param html: HTML template
* @param templateContext: object containing context to fetch
* @return {string} HTML with fetched context
*/
function fetchTemplateContext(html, templateContext){
for (const [key, value] of Object.entries(templateContext)) {
html = html.replaceAll('{'+key+'}', value);
}
return html;
}

/**
* Builds HTML from passed params and template name
* @param templateName: name of the template to fetch
* @param templateContext: properties from template to fetch
* @param requestArgs: request string arguments (optional)
* @returns built template string
*/
async function buildHTMLFromTemplate(templateName, templateContext = {}, requestArgs=''){
if(!configData['DISABLE_CACHING'] && loadedComponents.hasOwnProperty(templateName) && !requestArgs){
const html = loadedComponents[templateName];
return fetchTemplateContext(html, templateContext);
}else {
return await fetch(`${configData['currentURLBase']}/components/${templateName}?${requestArgs}`)
.then((response) => {
if (response.ok) {
return response.text();
}
throw `template unreachable (HTTP STATUS:${response.status}: ${response.statusText})`
})
.then((html) => {
if (!(configData['DISABLE_CACHING'] || loadedComponents.hasOwnProperty(templateName) || requestArgs)) {
loadedComponents[templateName] = html;
}
return fetchTemplateContext(html, templateContext);
}).catch(err => console.warn(`Failed to fetch template for ${templateName}: ${err}`));
}
}


/**
* Get Node id based on language key
* @param cid: desired conversation id
* @param key: language key (e.g. 'en')
* @param inputType: type of the language input to apply (incoming or outcoming)
* @return {string} ID of Node
*/
function getLangOptionID(cid, key, inputType='incoming'){
return `language-option-${cid}-${inputType}-${key}`;
}

/**
* Build language selection HTML based on provided params
* @param cid: desired conversation id
* @param key: language key (e.g 'en')
* @param name: name of the language (e.g. English)
* @param icon: language icon (refers to flag-icon specs)
* @param inputType: type of the language input to apply (incoming or outcoming)
* @return {string} formatted langSelectPattern
*/
async function buildLangOptionHTML(cid, key, name, icon, inputType){
return await buildHTMLFromTemplate('lang_option', {
'itemId': getLangOptionID(cid, key, inputType),
'key': key,
'name': name,
'icon': icon
})
}

/**
* Builds user message HTML
* @param userData: data of message sender
* @param messageID: id of user message
* @param messageText: text of user message
* @param timeCreated: date of creation
* @param isMine: if message was emitted by current user
* @param isAudio: if message is audio message (defaults to '0')
* @param isAnnouncement: is message if announcement (defaults to '0')
* @returns {string}: constructed HTML out of input params
*/
async function buildUserMessageHTML(userData, messageID, messageText, timeCreated, isMine, isAudio = '0', isAnnouncement = '0'){
const messageTime = getTimeFromTimestamp(timeCreated);
let imageComponent;
let shortedNick = `${userData['nickname'][0]}${userData['nickname'][userData['nickname'].length - 1]}`;
if (userData.hasOwnProperty('avatar') && userData['avatar']){
imageComponent = `<img alt="${shortedNick}" onerror="handleImgError(this);" src="${configData["CHAT_SERVER_URL_BASE"]}/files/avatar/${userData['_id']}" loading="lazy">`
}
else{
imageComponent = `<p>${shortedNick}</p>`;
}
const messageClass = isAnnouncement === '1'?'announcement':isMine?'in':'out';
const messageOrientation = isMine?'right': 'left';
let minificationEnabled = currentUser?.preferences?.minify_messages === '1';
if(isAnnouncement === '1'){
minificationEnabled = false;
}
let templateSuffix = minificationEnabled? '_minified': '';
const templateName = isAudio === '1'?`user_message_audio${templateSuffix}`: `user_message${templateSuffix}`;
if (isAudio === '0') {
messageText = messageText.replaceAll( '\n', '<br>' );
}
return await buildHTMLFromTemplate(templateName,
{'message_class': messageClass,
'is_announcement': isAnnouncement,
'image_component': imageComponent,
'message_id':messageID,
'nickname': userData['nickname'],
'message_text':messageText,
'message_orientation': messageOrientation,
'audio_url': `${configData["CHAT_SERVER_URL_BASE"]}/files/audio/${messageID}`,
'message_time': messageTime});
}

/**
*
* @param nick: nickname to shorten
* @return {string} - shortened nickname
*/
const shrinkNickname = (nick) => {
return `${nick[0]}${nick[nick.length - 1]}`;
}


/**
* Builds Prompt Skin HTML for submind responses
* @param promptID: target prompt id
* @param submindID: user id of submind
* @param submindUserData: user data of submind
* @param submindResponse: Responding shout of submind to incoming prompt
* @param submindOpinion: Discussion shout of submind to incoming prompt
* @param submindVote: Vote of submind in prompt
* @return {Promise<string|void>} - Submind Data HTML populated with provided data
*/
async function buildSubmindHTML(promptID, submindID, submindUserData, submindResponse, submindOpinion, submindVote) {
const userNickname = shrinkNickname(submindUserData['nickname']);
return await buildHTMLFromTemplate("prompt_participant",
{
'prompt_id': promptID,
'user_id': submindID,
'user_first_name': submindUserData['first_name'],
'user_last_name': submindUserData['last_name'],
'user_nickname': userNickname,
'user_avatar': `${configData["CHAT_SERVER_URL_BASE"]}/files/avatar/${submindID}`,
'response': submindResponse,
'opinion': submindOpinion,
'vote':submindVote});
}


/**
* Gets winner text based on the provided winner data
* @param winner: provided winner
* @return {string} generated winner text
*/
const getPromptWinnerText = (winner) => {
let res;
if (winner){
res = `Selected winner "${winner}"`;
}else{
res = 'Consensus not reached';
}
return res;
}


/**
* Builds prompt HTML from received prompt data
* @param prompt: prompt object
* @return Prompt HTML
*/
async function buildPromptHTML(prompt) {
let submindsHTML = "";
const promptData = prompt['data'];
if (prompt['is_completed'] === '0'){
promptData['winner'] = `Prompt in progress
<div class="spinner-border spinner-border-sm text-dark" role="status">
<span class="sr-only">Loading...</span>
</div>`
}else {
promptData['winner'] = getPromptWinnerText(promptData['winner']);
}
const emptyAnswer = `<h4>-</h4>`;
for (const submindID of Array.from(setDefault(promptData, 'participating_subminds', []))) {
let submindUserData;
try {
const searchedKeys = ['proposed_responses', 'submind_opinions', 'votes'];
let isLegacy = false;
try {
submindUserData = prompt['user_mapping'][submindID][0];
} catch (e) {
console.warn('Detected legacy prompt structure');
submindUserData = {
'nickname': submindID,
'first_name': 'Klat',
'last_name': 'User'
}
isLegacy = true
}
const data = {}
searchedKeys.forEach(key=>{
try {
let value = promptData[key][submindID];
if (!isLegacy) {
value = prompt['message_mapping'][value][0]['message_text'];
}
if (!value) {
value = emptyAnswer
}
data[key] = value;
}catch (e) {
data[key] = emptyAnswer;
}
});
submindsHTML += await buildSubmindHTML(prompt['_id'], submindID, submindUserData,
data.proposed_responses, data.submind_opinions, data.votes);
}catch (e) {
console.log(`Malformed data for ${submindID} (prompt_id=${prompt['_id']}) ex=${e}`);
}
}
return await buildHTMLFromTemplate("prompt_table",
{'prompt_text': promptData['prompt_text'],
'selected_winner': promptData['winner'],
'prompt_participants_data': submindsHTML,
'prompt_id':prompt['_id'],
'cid': prompt['cid'],
'message_time': prompt['created_on']});
}

/**
* Gets user message HTML from received message data object
* @param message: Message Object received
* @param skin: conversation skin
* @return {Promise<string>} HTML by the provided message data
*/
async function messageHTMLFromData(message, skin=CONVERSATION_SKINS.BASE){
if (skin === CONVERSATION_SKINS.BASE) {
const isMine = currentUser && message['user_nickname'] === currentUser['nickname'];
return buildUserMessageHTML({
'avatar': message['user_avatar'],
'nickname': message['user_nickname'],
'_id': message['user_id']
},
message['message_id'],
message['message_text'],
message['created_on'],
isMine,
message?.is_audio,
message?.is_announcement);
} else if (skin === CONVERSATION_SKINS.PROMPTS){
return buildPromptHTML(message);
}
}

/**
* Builds HTML for received conversation data
* @param conversationData: JS Object containing conversation data of type:
* {
*     '_id': 'id of conversation',
*     'conversation_name': 'title of the conversation',
*     'chat_flow': [{
*         'user_nickname': 'nickname of sender',
*         'user_avatar': 'avatar of sender',
*         'message_id': 'id of the message',
*         'message_text': 'text of the message',
*         'created_on': 'creation time of the message'
*     }, ... (num of user messages returned)]
* }
* @param skin: conversation skin to build
* @returns {string} conversation HTML based on provided data
*/
async function buildConversationHTML(conversationData = {}, skin = CONVERSATION_SKINS.BASE){
const cid = conversationData['_id'];
const conversation_name = conversationData['conversation_name'];
let chatFlowHTML = "";
if(conversationData.hasOwnProperty('chat_flow')) {
for (const message of Array.from(conversationData['chat_flow'])) {
chatFlowHTML += await messageHTMLFromData(message, skin);
if (skin === CONVERSATION_SKINS.BASE) {
addConversationParticipant(cid, message['user_nickname']);
}
}
}else{
chatFlowHTML+=`<div class="blank_chat">No messages in this chat yet...</div>`;
}
return await buildHTMLFromTemplate('conversation',
{'cid': cid, 'conversation_name':conversation_name, 'chat_flow': chatFlowHTML}, `skin=${skin}`);
};

/**
* Builds suggestion HTML
* @param cid: target conversation id
* @param name: target conversation name
* @return {Promise<string|void>} HTML with fetched data
*/
const buildSuggestionHTML = async (cid, name) => {
return await buildHTMLFromTemplate('suggestion', {'cid': cid, 'conversation_name': name})
};const importConversationModal = $('#importConversationModal');
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
setChatState(cid,'active')
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
* @param appname: name of the application to export (defaults to Excel)
*/
const exportTablesToExcel = (function() {
let uri = 'data:application/vnd.ms-excel;base64,'
, tmplWorkbookXML = '<?xml version="1.0"?><?mso-application progid="Excel.Sheet"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">'
+ '<DocumentProperties xmlns="urn:schemas-microsoft-com:office:office"><Author>Axel Richter</Author><Created>{created}</Created></DocumentProperties>'
+ '<Styles>'
+ '<Style ss:ID="Currency"><NumberFormat ss:Format="Currency"></NumberFormat></Style>'
+ '<Style ss:ID="Date"><NumberFormat ss:Format="Medium Date"></NumberFormat></Style>'
+ '</Styles>'
+ '{worksheets}</Workbook>'
, tmplWorksheetXML = '<Worksheet ss:Name="{nameWS}"><Table>{rows}</Table></Worksheet>'
, tmplCellXML = '<Cell{attributeStyleID}{attributeFormula}><Data ss:Type="{nameType}">{data}</Data></Cell>'
, base64 = function(s) { return window.btoa(unescape(encodeURIComponent(s))) }
, format = function(s, c) { return s.replace(/{(\w+)}/g, function(m, p) { return c[p]; }) }
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
let dataType = tables[i].rows[j].cells[k].getAttribute("data-type");
let dataStyle = tables[i].rows[j].cells[k].getAttribute("data-style");
let dataValue = tables[i].rows[j].cells[k].getAttribute("data-value");
dataValue = (dataValue)?dataValue:tables[i].rows[j].cells[k].innerHTML;
let dataFormula = tables[i].rows[j].cells[k].getAttribute("data-formula");
dataFormula = (dataFormula)?dataFormula:(appname=='Calc' && dataType=='DateTime')?dataValue:null;
ctx = {  attributeStyleID: (dataStyle=='Currency' || dataStyle=='Date')?' ss:StyleID="'+dataStyle+'"':''
, nameType: (dataType=='Number' || dataType=='DateTime' || dataType=='Boolean' || dataType=='Error')?dataType:'String'
, data: (dataFormula)?'':dataValue
, attributeFormula: (dataFormula)?' ss:Formula="'+dataFormula+'"':''
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

ctx = {created: (new Date()).getTime(), worksheets: worksheetsXML};
workbookXML = format(tmplWorkbookXML, ctx);

console.log(workbookXML);

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
* Sends message based on input
* @param inputElem: input DOM element
* @param cid: conversation id
* @param repliedMessageId: replied message id
* @param isAudio: is message audio
* @param isAnnouncement: is message an announcement
*/
const sendMessage = async (inputElem, cid, repliedMessageId=null, isAudio='0', isAnnouncement='0') => {
const attachments = await saveAttachedFiles(cid);
if (Array.isArray(attachments)) {
emitUserMessage(inputElem, cid, repliedMessageId, attachments, isAudio, isAnnouncement);
}
inputElem.value = "";
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
const textInputElem = document.getElementById(conversationData['_id'] + '-input');

if (chatInputButton.hasAttribute('data-target-cid')) {
textInputElem.addEventListener('keyup', async (e)=>{
if (e.shiftKey && e.key === 'Enter'){
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
displayParticipantsCount(conversationData['_id']);
await initLanguageSelectors(conversationData['_id']);
await addRecorder(conversationData);


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
});
});
}

if (chatCloseButton.hasAttribute('data-target-cid')) {
chatCloseButton.addEventListener('click', async (e) => {
conversationHolder.removeChild(conversationParent);
await removeConversation(cid);
clearStateCache(cid);
});
}
// Hide close button for Nano Frames
if (configData.client === CLIENTS.NANO){
chatCloseButton.hidden = true;
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
* @param alertParent: parent of error alert (optional)
* @returns {Promise<{}>} promise resolving conversation data returned
*/
async function getConversationDataByInput(input="", skin=CONVERSATION_SKINS.BASE, firstMessageID=null, maxResults=10, alertParent=null){
let conversationData = {};
if(input && typeof input === "string"){
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
function refreshChatView(conversationContainer=null){
if (!conversationContainer){
conversationContainer = conversationBody;
}
Array.from(conversationContainer.getElementsByClassName('conversationContainer')).forEach(async conversation=>{
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
* @param conversationParentID: parent Node ID of the conversation
*/
async function displayConversation(searchStr, skin=CONVERSATION_SKINS.BASE, alertParentID = null, conversationParentID='conversationsBody'){
if (searchStr !== "") {
const alertParent = document.getElementById(alertParentID);
await getConversationDataByInput(searchStr, skin, null, 10, alertParent).then(async conversationData => {
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
else if (await isDisplayed(conversationData['_id'])) {
displayAlert(alertParent, 'Chat is already displayed', 'danger');
} else {
await buildConversation(conversationData, skin, true, conversationParentID);
if (skin === CONVERSATION_SKINS.BASE) {
for (const inputType of ['incoming', 'outcoming']) {
await requestTranslation( conversationData['_id'], null, null, inputType );
}
}
responseOk = true;
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

if (configData['client'] === CLIENTS.MAIN) {
document.addEventListener('supportedLanguagesLoaded', async (e)=>{
await refreshCurrentUser(false)
.then(async _ => await restoreChatAlignment())
.then(async _=>await refreshCurrentUser(true))
.then(async _=> await requestChatsLanguageRefresh())
.then(async _=> renderSuggestions());
});
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
});/**
* Collection of supported clients, current client is matched based on client configuration
* @type {{NANO: string, MAIN: string}}
*/
const CLIENTS = {
MAIN: 'main',
NANO: 'nano',
UNDEFINED: undefined
}

/**
* JS Object containing frontend configuration data
* @type {{staticFolder: string, currentURLBase: string, currentURLFull: (string|string|string|SVGAnimatedString|*), client: string}}
*/

let configData = {
'staticFolder': "../../static",
'currentURLBase': extractURLBase(),
'currentURLFull': window.location.href,
'client': typeof metaConfig !== 'undefined'? metaConfig?.client : CLIENTS.UNDEFINED
};

/**
* Default key for storing data in local storage
* @type {string}
*/
const conversationAlignmentKey = 'conversationAlignment';

/**
* Custom Event fired on configs ended up loading
* @type {CustomEvent<string>}
*/
const configFullLoadedEvent = new CustomEvent("configLoaded", { "detail": "Event that is fired when configs are loaded" });

/**
* Convenience method for getting URL base for current page
* @returns {string} constructed URL base
*/
function extractURLBase(){
return window.location.protocol + '//' + window.location.hostname + (window.location.port?':'+window.location.port:'');
}

/**
* Extracts json data from provided URL path
* @param urlPath: file path string
* @returns {Promise<* | {}>} promise that resolves data obtained from file path
*/
async function extractJsonData(urlPath=""){
return fetch(urlPath).then(response => {
if (response.ok){
return response.json();
}return  {};
});
}


document.addEventListener('DOMContentLoaded', async (e)=>{
if (configData['client'] === CLIENTS.MAIN) {
configData = Object.assign(configData, await extractJsonData(`${configData['currentURLBase']}/base/runtime_config`));
document.dispatchEvent(configFullLoadedEvent);
}
});
/**
* Gets time object from provided UNIX timestamp
* @param timestampCreated: UNIX timestamp (in seconds)
* @returns {string} string time (hours:minutes)
*/
function getTimeFromTimestamp(timestampCreated=0){
let date = new Date(timestampCreated * 1000);
let year = date.getFullYear().toString();
let month = date.getMonth()+1;
month = month>=10?month.toString():'0'+month.toString();
let day = date.getDate();

day = day>=10?day.toString():'0'+day.toString();
const hours = date.getHours().toString();
let minutes = date.getMinutes();
minutes = minutes>=10?minutes.toString():'0'+minutes.toString();
return strFmtDate(year, month, day, hours, minutes, null);
}

/**
* Composes date based on input params
* @param year: desired year
* @param month: desired month
* @param day: desired day
* @param hours: num of hours
* @param minutes: minutes
* @param seconds: seconds
* @return date string
*/
function strFmtDate(year, month, day, hours, minutes, seconds){
let finalDate = "";
if(year && month && day){
finalDate+=`${year}-${month}-${day}`
}
if(hours && minutes) {
finalDate += ` ${hours}:${minutes}`
if (seconds) {
finalDate += `:${seconds}`
}
}
return finalDate;
}const DATABASES = {
CHATS: 'chats'
}
const DB_TABLES = {
CHAT_ALIGNMENT: 'chat_alignment'
}
const __db_instances = {}
const __db_definitions = {
"chats": {
"chat_alignment": `cid, added_on, skin`
}
}

/**
* Gets database and table from name
* @param db: database name to get
* @param table: table name to get
* @return {Table} Dexie database object under specified table
*/
const getDb = (db, table) => {
let _instance;
if (!Object.keys(__db_instances).includes(db)){
_instance = new Dexie(name);
if (Object.keys(__db_definitions).includes(db)){
_instance.version(1).stores(__db_definitions[db]);
}
__db_instances[db] = _instance;
}else{
_instance = __db_instances[db];
}
return _instance[table];
}/**
* Downloads desired content
* @param content: content to download
* @param filename: name of the file to download
* @param contentType: type of the content
*/
function download(content, filename, contentType='application/octet-stream')
{
if(content) {
const a = document.createElement('a');
const blob = new Blob([content], {'type':contentType});
a.href = window.URL.createObjectURL(blob);
a.target = 'blank';
a.download = filename;
a.click();
window.URL.revokeObjectURL(content);
}else{
console.warn('Skipping downloading as content is invalid')
}
}

/**
* Handles error while loading the image data
* @param image: target image Node
*/
function handleImgError(image) {
image.parentElement.insertAdjacentHTML('afterbegin',`<p>${image.getAttribute('alt')}</p>`);
image.parentElement.removeChild(image);
}const REQUEST_METHODS = {
GET: 'GET',
PUT: 'PUT',
DELETE: 'DELETE',
POST: 'POST'
}


const getSessionToken = () => {
return localStorage.getItem('session') || '';
}

const setSessionToken = (val) => {
const currentValue = getSessionToken();
localStorage.setItem( 'session', val );
if (currentValue && currentValue!==val) {
location.reload();
}
}

const fetchServer = async (urlSuffix, method=REQUEST_METHODS.GET, body=null, noCors=false) => {
const options = {
method: method,
headers: new Headers({'Authorization': getSessionToken()})
}
if (noCors){
options['mode'] = 'no-cors';
}
if (body){
options['body'] = body;
}
return fetch(`${configData["CHAT_SERVER_URL_BASE"]}/${urlSuffix}`, options).then(async response => {
if (response.status === 401){
const responseJson = await response.json();
if (responseJson['msg'] === 'Session Expired'){
localStorage.removeItem('session');
location.reload();
}
}
return response;
});
};/**
* Returns preferred language specified in provided cid
* @param cid: provided conversation id
* @param inputType: type of the language preference to fetch:
* "incoming" - for external shouts, "outcoming" - for emitted shouts
*
* @return preferred lang by cid or "en"
*/
function getPreferredLanguage(cid, inputType='incoming'){
let preferredLang = 'en';
try {
preferredLang = getChatLanguageMapping(cid, inputType);
}catch (e) {
console.warn(`Failed to getChatLanguageMapping - ${e}`)
}
return preferredLang;
}

/**
* Returns preferred language specified in provided cid
* @param cid: provided conversation id
* @param lang: new preferred language to set
* @param inputType: type of the language preference to fetch:
* @param updateDB: to update user preferences in database
* @param updateDBOnly: to update user preferences in database only (without translation request)
* "incoming" - for external shouts, "outcoming" - for emitted shouts
*/
async function setPreferredLanguage(cid, lang, inputType='incoming', updateDB=true, updateDBOnly=false){
let isOk = false;
if (updateDB) {
const formData = new FormData();
formData.append('lang', lang);
isOk = await fetchServer(`preferences/update_language/${cid}/${inputType}`,REQUEST_METHODS.POST, formData)
.then(res => {
return res.ok;
});
} if ((isOk || !updateDB) && !updateDBOnly) {
updateChatLanguageMapping(cid, inputType, lang);
await requestTranslation(cid, null, null, inputType);
}
}

/**
* Fetches supported languages
*/
async function fetchSupportedLanguages(){
const query_url = `language_api/settings`;
return await fetchServer(query_url)
.then(response => {
if(response.ok){
return response.json();
}else{
console.log(`failed to fetch supported languages - ${response.statusText}`)
throw response.statusText;
}
})
.then(data => {
configData['supportedLanguages'] = data['supported_languages'];
console.info(`supported languages updated - ${JSON.stringify(configData['supportedLanguages'])}`)
}).catch(err=> console.warn('Failed to fulfill request due to error:',err));
}

/**
* Sends request for updating target conversation(s) content to the desired language
* @param cid: conversation id to bound request to
* @param shouts: list of shout ids to bound request to
* @param lang: language to apply (defaults to preferred language of each fetched conversation)
* @param inputType: type of the language input to apply (incoming or outcoming)
* @param translateToBaseLang: to translate provided items to the system base lang (based on preferred)
*/
async function requestTranslation(cid=null, shouts=null, lang=null, inputType='incoming', translateToBaseLang=false){
let requestBody = {chat_mapping: {}};
const skin = await getCurrentSkin(cid);
if(cid && await isDisplayed(cid) && skin === CONVERSATION_SKINS.BASE){
lang = lang || getPreferredLanguage(cid, inputType);
if (lang !== 'en' && getMessagesOfCID(cid).length > 0){
setChatState(cid, 'updating', 'Applying New Language...');
}
if(shouts && !Array.isArray(shouts)){
shouts = [shouts];
}
if (!shouts && inputType){
shouts = getMessagesOfCID(cid, getMessageReferType(inputType), skin, true);
if (shouts.length === 0){
console.log(`${cid} yet has no shouts matching type=${inputType}`);
setChatState(cid, 'active');
return
}
}
setDefault(requestBody.chat_mapping, cid, {});
requestBody.chat_mapping[cid] = {'lang': lang, 'shouts': shouts || []}
if (translateToBaseLang){
requestBody.chat_mapping[cid]['source_lang'] = getPreferredLanguage(cid);
}
}else{
requestBody.chat_mapping = getChatLanguageMapping();
if (!requestBody.chat_mapping){
console.log('Chat mapping is undefined - returning');
return
}
}
requestBody['user'] = currentUser['_id'];
requestBody['inputType'] = inputType;
console.debug(`requestBody = ${JSON.stringify(requestBody)}`);
socket.emitAuthorized('request_translate', requestBody);
}

/**
* Sets selected language to the target language selector
* @param clickedItem: Language selector element clicked
* @param cid: target conversation id
* @param inputType: type of the language input to apply (incoming or outcoming)
*/
async function setSelectedLang(clickedItem, cid, inputType="incoming"){
const selectedLangNode = document.getElementById(`language-selected-${cid}-${inputType}`);
const selectedLangList = document.getElementById(`language-list-${cid}-${inputType}`);

// console.log('emitted lang update')
const preferredLang = getPreferredLanguage(cid, inputType);
const preferredLangProps = configData['supportedLanguages'][preferredLang];
const newKey = clickedItem.getAttribute('data-lang');
const newPreferredLangProps = configData['supportedLanguages'][newKey];

const direction = inputType === 'incoming'?'down':'up';
selectedLangNode.innerHTML = await buildHTMLFromTemplate('selected_lang', {'key': newKey, 'name': newPreferredLangProps['name'], 'icon': newPreferredLangProps['icon'], 'direction': direction})
if (preferredLangProps) {
selectedLangList.getElementsByClassName('lang-container')[0].insertAdjacentHTML('beforeend', await buildLangOptionHTML(cid, preferredLang, preferredLangProps['name'], preferredLangProps['icon'], inputType));
}
else{
console.warn(`"${preferredLang}" is set to be preferred but currently not supported`)
}
if (clickedItem.parentNode){
clickedItem.parentNode.removeChild(clickedItem);
}
console.log(`cid=${cid};new preferredLang=${newKey}, inputType=${inputType}`);
await setPreferredLanguage(cid, newKey, inputType, true);
const insertedNode = document.getElementById(getLangOptionID(cid, preferredLang, inputType));
insertedNode.addEventListener('click', async (e)=> {
e.preventDefault();
await setSelectedLang(insertedNode, cid, inputType);
});
}

/**
* Initialize language selector for conversation
* @param cid: target conversation id
* @param inputType: type of the language input to apply (incoming or outcoming)
*/
async function initLanguageSelector(cid, inputType="incoming"){
let preferredLang = getPreferredLanguage(cid, inputType);
const supportedLanguages = configData['supportedLanguages'];
if (!supportedLanguages.hasOwnProperty(preferredLang)){
preferredLang = 'en';
}
const selectedLangNode = document.getElementById(`language-selected-${cid}-${inputType}`);
const langList = document.getElementById(`language-list-${cid}-${inputType}`);
if (langList) {
const langListContainer = langList.getElementsByClassName('lang-container')[0]

if (langListContainer) {
langListContainer.innerHTML = "";
}

// selectedLangNode.innerHTML = "";
for (const [key, value] of Object.entries(supportedLanguages)) {

if (key === preferredLang) {
const direction = inputType === 'incoming' ? 'down' : 'up';
selectedLangNode.innerHTML = await buildHTMLFromTemplate('selected_lang',
{'key': key, 'name': value['name'], 'icon': value['icon'], 'direction': direction})
} else {
langListContainer.insertAdjacentHTML('beforeend', await buildLangOptionHTML(cid, key, value['name'], value['icon'], inputType));
const itemNode = document.getElementById(getLangOptionID(cid, key, inputType));
itemNode.addEventListener('click', async (e) => {
e.preventDefault();
await setSelectedLang(itemNode, cid, inputType)
});
}
}
}
}

/**
* Inits both incoming and outcoming language selectors
* @param cid: target conversation id
*/
const initLanguageSelectors = async (cid) => {
for (const inputType of ['incoming', 'outcoming']){
await initLanguageSelector(cid, inputType);
}
}


function getMessageReferType(inputType){
return inputType === 'incoming'?MESSAGE_REFER_TYPE.OTHERS: MESSAGE_REFER_TYPE.MINE;
}


/**
* Sends request to server for chat language refreshing
*/
async function requestChatsLanguageRefresh(){
const languageMapping = currentUser?.preferences?.chat_language_mapping || {};
console.log(`languageMapping=${JSON.stringify(languageMapping)}`)
for (const [cid, value] of Object.entries(languageMapping)) {
if (await isDisplayed(cid)) {
for (const inputType of ['incoming', 'outcoming']) {
const lang = value[inputType] || 'en';
if (lang !== 'en') {
await setPreferredLanguage(cid, lang, inputType, false);
}
}
}
}
console.log(`chatLanguageMapping=${JSON.stringify(getChatLanguageMapping())}`)
}

/**
* Applies translation based on received data
* @param data: translation object received
* Note: data should be of format:
* {
*     'cid': {'message1':'translation of message 1',
*             'message2':'translation of message 2'}
* }
*/
async function applyTranslations(data){
const inputType = setDefault(data, 'input_type', 'incoming');
for (const [cid, messageTranslations] of Object.entries(data['translations'])) {

if(await getCurrentSkin(cid) !== CONVERSATION_SKINS.BASE){
console.log(`cid=${cid} is not displayed, skipping translations population`)
continue;
}

setChatState(cid, 'active');

console.debug(`Fetching translation of ${cid}`);
// console.debug(`translations=${JSON.stringify(messageTranslations)}`)

const messageTranslationsShouts = messageTranslations['shouts'];
if (messageTranslationsShouts) {
const messageReferType = getMessageReferType(inputType);
const messages = getMessagesOfCID(cid, messageReferType);
Array.from(messages).forEach(message => {
const messageID = message.id;
let repliedMessage = null;
let repliedMessageID = null;
try {
repliedMessage = message.getElementsByClassName('reply-placeholder')[0].getElementsByClassName('reply-text')[0];
repliedMessageID = repliedMessage.getAttribute('data-replied-id')
// console.debug(`repliedMessageID=${repliedMessageID}`)
} catch (e) {
// console.debug(`replied message not found for ${messageID}`);
}
if (messageID in messageTranslationsShouts) {
message.getElementsByClassName('message-text')[0].innerHTML = messageTranslationsShouts[messageID];
}
if (repliedMessageID && repliedMessageID in messageTranslationsShouts) {
repliedMessage.innerHTML = messageTranslationsShouts[repliedMessageID];
}
});
await initLanguageSelector(cid, inputType);
}
}
}


const getChatLanguageMapping = (cid=null, inputType=null) => {
let res =  setDefault(setDefault(currentUser, 'preferences', {}), 'chat_language_mapping', {});
if (cid){
res = setDefault(res, cid, {});
}if (inputType){
res = setDefault(res, inputType, 'en');
}
return res;
}

const updateChatLanguageMapping = (cid, inputType, lang) => {
setDefault(currentUser.preferences.chat_language_mapping, cid, {})[inputType] = lang;
console.log(`cid=${cid},inputType=${inputType} updated to lang=${lang}`);
}

/**
* Custom Event fired on supported languages init
* @type {CustomEvent<string>}
*/
const supportedLanguagesLoadedEvent = new CustomEvent("supportedLanguagesLoaded", { "detail": "Event that is fired when system supported languages are loaded" });

document.addEventListener('DOMContentLoaded', (_)=>{
document.addEventListener('configLoaded',async (_)=>{
await fetchSupportedLanguages().then(_ => document.dispatchEvent(supportedLanguagesLoadedEvent));
});
});/**
* Adds speaking callback for the message
* @param cid: id of the conversation
* @param messageID: id of the message
*/
function addTTSCallback(cid, messageID){
const speakingButton = document.getElementById(`${messageID}_speak`);
if (speakingButton) {
speakingButton.addEventListener('click', (e) => {
e.preventDefault();
getTTS(cid, messageID, getPreferredLanguage(cid));
setChatState(cid, 'updating', `Fetching TTS...`)
});
}
}

/**
* Adds speaking callback for the message
* @param cid: id of the conversation
* @param messageID: id of the message
*/
function addSTTCallback(cid, messageID){
const sttButton = document.getElementById(`${messageID}_text`);
if (sttButton) {
sttButton.addEventListener('click', (e) => {
e.preventDefault();
const sttContent = document.getElementById(`${messageID}-stt`);
if (sttContent){
sttContent.innerHTML = `<div class="text-center">
Waiting for STT...  <div class="spinner-border spinner-border-sm" role="status">
<span class="sr-only">Loading...</span>
</div>
</div>`;
sttContent.style.setProperty('display', 'block', 'important');
getSTT(cid, messageID, getPreferredLanguage(cid));
}
});
}
}

/**
* Attaches STT capabilities for audio messages and TTS capabilities for text messages
* @param cid: parent conversation id
* @param messageID: target message id
* @param isAudio: if its an audio message (defaults to '0')
*/
function addMessageTransformCallback(cid, messageID, isAudio='0'){
if (isAudio === '1'){
addSTTCallback(cid, messageID);
}else{
addTTSCallback(cid, messageID);
}
}


/**
* Attaches STT capabilities for audio messages and TTS capabilities for text messages
* @param conversationData: conversation data object
*/
function addCommunicationChannelTransformCallback(conversationData) {
if (conversationData.hasOwnProperty('chat_flow')) {
getUserMessages(conversationData).forEach(message => {
addMessageTransformCallback(conversationData['_id'], message['message_id'], message?.is_audio);
});
}
}/**
* Returns DOM container for message elements under specific conversation id
* @param cid: conversation id to consider
* @return {Element} DOM container for message elements of considered conversation
*/
const getMessageListContainer = (cid) => {
const cidElem = document.getElementById(cid);
if(cidElem){
return cidElem.getElementsByClassName('card-body')[0].getElementsByClassName('chat-list')[0]
}
}

/**
* Gets message node from the message container
* @param messageContainer: DOM Message Container element to consider
* @param skin: target conversation skin to consider
* @return {HTMLElement} ID of the message
*/
const getMessageNode = (messageContainer, skin) => {
if (skin === CONVERSATION_SKINS.PROMPTS){
return messageContainer.getElementsByTagName('table')[0];
}else {
return messageContainer.getElementsByClassName('chat-body')[0].getElementsByClassName('chat-message')[0];
}
}

/**
* Adds new message to desired conversation id
* @param cid: desired conversation id
* @param userID: message sender id
* @param messageID: id of sent message (gets generated if null)
* @param messageText: text of the message
* @param timeCreated: timestamp for message creation
* @param repliedMessageID: id of the replied message (optional)
* @param attachments: array of attachments to add (optional)
* @param isAudio: is audio message (defaults to '0')
* @param isAnnouncement: is message an announcement (defaults to "0")
* @returns {Promise<null|number>}: promise resolving id of added message, -1 if failed to resolve message id creation
*/
async function addNewMessage(cid, userID=null, messageID=null, messageText, timeCreated, repliedMessageID=null, attachments=[], isAudio='0', isAnnouncement='0'){
const messageList = getMessageListContainer(cid);
if(messageList){
let userData;
const isMine = userID === currentUser['_id'];
if(isMine) {
userData = currentUser;
}else{
userData = await getUserData(userID);
}
if(!messageID) {
messageID = generateUUID();
}
let messageHTML = await buildUserMessageHTML(userData, messageID, messageText, timeCreated, isMine, isAudio, isAnnouncement);
const blankChat = messageList.getElementsByClassName('blank_chat');
if(blankChat.length>0){
messageList.removeChild(blankChat[0]);
}
messageList.insertAdjacentHTML('beforeend', messageHTML);
resolveMessageAttachments(cid, messageID, attachments);
resolveUserReply(messageID, repliedMessageID);
addProfileDisplay(cid, messageID);
addConversationParticipant(cid, userData['nickname'], true);
scrollOnNewMessage(messageList);
return messageID;
}
}

const PROMPT_STATES = {
1: 'RESP',
2: 'DISC',
3: 'VOTE'
}

/**
* Returns HTML Element representing user row in prompt
* @param promptID: target prompt id
* @param userID: target user id
* @return {HTMLElement}: HTML Element containing user prompt data
*/
const getUserPromptTR = (promptID, userID) => {
return document.getElementById(`${promptID}_${userID}_prompt_row`);
}

/**
* Adds prompt message of specified user id
* @param cid: target conversation id
* @param userID: target submind user id
* @param messageText: message of submind
* @param promptId: target prompt id
* @param promptState: prompt state to consider
*/
async function addPromptMessage(cid, userID, messageText, promptId, promptState){
const tableBody = document.getElementById(`${promptId}_tbody`);
if (await getCurrentSkin(cid) === CONVERSATION_SKINS.PROMPTS){
try {
promptState = PROMPT_STATES[promptState].toLowerCase();
if (!getUserPromptTR(promptId, userID)) {
const userData = await getUserData(userID);
const newUserRow = await buildSubmindHTML(promptId, userID, userData, '', '', '');
tableBody.insertAdjacentHTML('beforeend', newUserRow);
}
try {
const messageElem = document.getElementById(`${promptId}_${userID}_${promptState}`);
messageElem.innerText = messageText;
} catch (e) {
console.warn(`Failed to add prompt message (${cid},${userID}, ${messageText}, ${promptId}, ${promptState}) - ${e}`)
}
} catch (e) {
console.info(`Skipping message of invalid prompt state - ${promptState}`);
}
}
}

/**
* Gets list of the next n-older messages
* @param cid: target conversation id
* @param skin: target conversation skin
* @param numMessages: number of messages to add
*/
function addOldMessages(cid, skin=CONVERSATION_SKINS.BASE, numMessages = 10){
const messageContainer = getMessageListContainer(cid);
if(messageContainer.children.length > 0) {
const firstMessageItem = messageContainer.children[0];
const firstMessageID = getMessageNode(firstMessageItem, skin).id;
getConversationDataByInput(cid, skin, firstMessageID).then(async conversationData => {
if (messageContainer) {
const userMessageList = getUserMessages(conversationData);
userMessageList.sort((a, b) => {
a['created_on'] - b['created_on'];
}).reverse();
for (const message of userMessageList) {
const messageHTML = await messageHTMLFromData(message, skin);
messageContainer.insertAdjacentHTML('afterbegin', messageHTML);
}
initMessages(conversationData, skin);
}
}).then(_=>{
firstMessageItem.scrollIntoView({behavior: "smooth"});
});
}
}

/**
* Array of user messages in given conversation
* @param conversationData: Conversation Data object to fetch
*/
const getUserMessages = (conversationData) => {
try {
return Array.from(conversationData['chat_flow']);
} catch{
return [];
}
}

/**
* Initializes listener for loading old message on scrolling conversation box
* @param conversationData: Conversation Data object to fetch
* @param skin: conversation skin to apply
*/
function initLoadOldMessages(conversationData, skin) {
const cid = conversationData['_id'];
const messageList = getMessageListContainer(cid);
const messageListParent = messageList.parentElement;
setDefault(setDefault(conversationState, cid, {}),'lastScrollY', 0);
messageListParent.addEventListener("scroll", async (e) => {
const oldScrollPosition = conversationState[cid]['scrollY'];
conversationState[cid]['scrollY'] = e.target.scrollTop;
if (oldScrollPosition > conversationState[cid]['scrollY'] &&
!conversationState[cid]['all_messages_displayed'] &&
conversationState[cid]['scrollY'] === 0) {
setChatState(cid, 'updating', 'Loading messages...')
addOldMessages(cid, skin);
for(const inputType of ['incoming', 'outcoming']){
await requestTranslation(cid, null, null, inputType);
}
setTimeout( () => {
setChatState(cid, 'active');
}, 700);
}
});
}

/**
* Adds callback for showing profile information on profile avatar click
* @param cid: target conversation id
* @param messageId: target message id
*/
function addProfileDisplay(cid, messageId){
const messageAvatar = document.getElementById(`${messageId}_avatar`);
if (messageAvatar){
messageAvatar.addEventListener('click', async (e)=>{
const userNickname = messageAvatar.getAttribute('data-target');
if(userNickname && configData.client === CLIENTS.MAIN) await showProfileModal(userNickname)
});
}
}


/**
* Inits addProfileDisplay() on each message of provided conversation
* @param conversationData: target conversation data
*/
function initProfileDisplay(conversationData){
getUserMessages(conversationData).forEach(message => {
addProfileDisplay(conversationData['_id'], message['message_id']);
});
}


/**
* Initializes messages based on provided conversation aata
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
* @param skin: target conversation skin to consider
*/
function initMessages(conversationData, skin = CONVERSATION_SKINS.BASE){
if (skin === CONVERSATION_SKINS.BASE) {
initProfileDisplay(conversationData);
attachReplies(conversationData);
addAttachments(conversationData);
addCommunicationChannelTransformCallback(conversationData);
}
// common logic
initLoadOldMessages(conversationData, skin);
}

/**
* Emits user message to Socket IO Server
* @param textInputElem: DOM Element with input text (audio object if isAudio=true)
* @param cid: Conversation ID
* @param repliedMessageID: ID of replied message
* @param attachments: list of attachments file names
* @param isAudio: is audio message being emitted (defaults to '0')
* @param isAnnouncement: is message an announcement (defaults to '0')
*/
function emitUserMessage(textInputElem, cid, repliedMessageID=null, attachments= [], isAudio='0', isAnnouncement='0'){
if(isAudio === '1' || textInputElem && textInputElem.value){
const timeCreated = getCurrentTimestamp();
let messageText;
if (isAudio === '1'){
messageText = textInputElem;
}else {
messageText = textInputElem.value;
}
addNewMessage(cid, currentUser['_id'],null, messageText, timeCreated,repliedMessageID,attachments, isAudio, isAnnouncement).then(async messageID=>{
const preferredShoutLang = getPreferredLanguage(cid, 'outcoming');
socket.emitAuthorized('user_message',
{'cid':cid,
'userID':currentUser['_id'],
'messageText':messageText,
'messageID':messageID,
'lang': preferredShoutLang,
'attachments': attachments,
'isAudio': isAudio,
'isAnnouncement': isAnnouncement,
'timeCreated':timeCreated
});
if(preferredShoutLang !== 'en'){
await requestTranslation(cid, messageID, 'en', 'outcoming', true);
}
addMessageTransformCallback(cid, messageID, isAudio);
});
if (isAudio === '0'){
textInputElem.value = "";
}
}
}/**
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
const replyHTML = `<a class="reply-text" data-replied-id="${repliedID}">
${repliedText}
</a>`;
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
}const MessageScrollPosition = {
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
}let socket;

const sioTriggeringEvents = ['configLoaded', 'configNanoLoaded'];

sioTriggeringEvents.forEach(event=>{
document.addEventListener(event,(e)=>{
socket = initSIO();
});
});

/**
* Inits socket io client listener by attaching relevant listeners on message channels
* @return {Socket} Socket IO client instance
*/
function initSIO(){

const sioServerURL = configData['CHAT_SERVER_URL_BASE'];
const socket = io(sioServerURL, {transports: ['polling'], extraHeaders: {
"session": getSessionToken()
}});

socket.__proto__.emitAuthorized = (event, data) => {
socket.io.opts.extraHeaders.session = getSessionToken();
return socket.emit(event, data);
}

socket.on('auth_expired', ()=>{
console.log('Authorization Token expired, refreshing...')
location.reload();
});

socket.on('connect', () => {
console.info(`Socket IO Connected to Server: ${sioServerURL}`)
});

socket.on("connect_error", (err) => {
console.log(`connect_error due to ${err.message}`);
});

socket.on('new_prompt_created', async (prompt) => {
const messageContainer = getMessageListContainer(prompt['cid']);
const promptID = prompt['_id'];
if (await getCurrentSkin(prompt['cid']) === CONVERSATION_SKINS.PROMPTS) {
if (!document.getElementById( promptID )) {
const messageHTML = await buildPromptHTML( prompt );
messageContainer.insertAdjacentHTML( 'beforeend', messageHTML );
}
}
});

socket.on('new_message', async (data) => {
console.debug('received new_message -> ', data)
const msgData = JSON.parse(data);
const skin = await getCurrentSkin(msgData['cid']);
if (skin === CONVERSATION_SKINS.BASE) {
const preferredLang = getPreferredLanguage(msgData['cid']);
if (data?.lang !== preferredLang) {
await requestTranslation(msgData['cid'], msgData['messageID']);
}
await addNewMessage(msgData['cid'], msgData['userID'], msgData['messageID'], msgData['messageText'], msgData['timeCreated'], msgData['repliedMessage'], msgData['attachments'], msgData?.isAudio, msgData?.isAnnouncement)
.catch(err => console.error('Error occurred while adding new message: ', err));
addMessageTransformCallback(msgData['cid'], msgData['messageID'], msgData?.isAudio);
}
});

socket.on('new_prompt_message', async (message) => {
await addPromptMessage(message['cid'], message['userID'], message['messageText'], message['promptID'], message['promptState'])
.catch(err => console.error('Error occurred while adding new prompt data: ', err));
});

socket.on('set_prompt_completed', async (data) => {
const promptID = data['prompt_id'];
const promptElem = document.getElementById(promptID);
console.info(`setting prompt_id=${promptID} as completed`);
if (promptElem){
const promptWinner = document.getElementById(`${promptID}_winner`);
promptWinner.innerText = getPromptWinnerText(data['winner']);
}else {
console.warn(`Failed to get HTML element from prompt_id=${promptID}`);
}
});

socket.on('translation_response', async (data) => {
console.log('translation_response: ', data)
await applyTranslations(data);
});

socket.on('incoming_tts', async (data)=> {
console.log('received incoming stt audio');
playTTS(data['cid'], data['lang'], data['audio_data']);
});

socket.on('incoming_stt', async (data)=>{
console.log('received incoming stt response');
showSTT(data['message_id'], data['lang'], data['message_text']);
});

// socket.on('updated_shouts', async (data) =>{
//     const inputType = data['input_type'];
//     for (const [cid, shouts] of Object.entries(data['translations'])){
//        if (await getCurrentSkin(cid) === CONVERSATION_SKINS.BASE){
//            await requestTranslation(cid, shouts, null, inputType);
//        }
//    }
// });

return socket;
}/**
* Generic function to play base64 audio file (currently only .wav format is supported)
* @param audio_data: base64 encoded audio data
*/
function play(audio_data){
const df = document.createDocumentFragment();
const audio = new Audio("data:audio/wav;base64," + audio_data);
df.appendChild(audio);
audio.addEventListener('ended', function () {df.removeChild(audio);});
audio.play().catch(err=> console.warn(`Failed to play audio_data = ${err}`));
}

/**
* Plays received TTS response
* @param cid: target conversation id
* @param lang: language of playing
* @param audio_data: audio data to play
*/
function playTTS(cid, lang, audio_data){
setChatState(cid, 'updating', 'Playing received audio');
play(audio_data);
setChatState(cid, 'active');
}

/**
* Shows STT response of audio message
* @param message_id: id of the audio message
* @param lang: language of response (text is not shown if language differs from current preference)
* @param message_text: message text to display
*/
function showSTT(message_id, lang, message_text){
// TODO: skip showing text when preferred language changed
// console.log(`showing: message_id=${message_id}, lang=${lang}, message_text=${message_text}`);
const messageSTTContent = document.getElementById(`${message_id}-stt`);
if(messageSTTContent && message_text){
messageSTTContent.innerText = '"' + message_text + '"';
}
}

/**
* Requests TTS for provider params
* @param cid: target conversation id
* @param message_id: target message id
* @param lang: target language
* @param gender: gender of speaker
*/
function getTTS(cid, message_id, lang, gender='female'){
// TODO: consider multi-gender voices in future
socket.emitAuthorized('request_tts', {'cid':cid,
'user_id':currentUser['_id'],
'message_id':message_id,
'lang':lang});
}


/**
* Requests STT for provider message params
* @param cid: target conversation id
* @param message_id: target message id
* @param lang: target language
*/
function getSTT(cid, message_id, lang){
socket.emitAuthorized('request_stt', {'cid':cid,
'user_id':currentUser['_id'],
'message_id':message_id,
'lang':lang});
}

/**
* Records audio from the client browser
* @param cid: target conversation id
* @return {Promise} recorder instance with following properties:
* - start() to start recording
* - stop() to end recording
*/
const recordAudio = (cid) => {
return new Promise(resolve => {
navigator.mediaDevices.getUserMedia({ audio: true })
.then(stream => {
const mediaRecorder = new MediaRecorder(stream);
const audioChunks = [];

mediaRecorder.addEventListener("dataavailable", event => {
audioChunks.push(event.data);
});

const start = () => {
mediaRecorder.start();
};

const stop = () => {
return new Promise(resolve => {
mediaRecorder.addEventListener("stop", () => {
const audioBlob = new Blob(audioChunks, { 'type' : 'audio/wav; codecs=0' });
const audioUrl = URL.createObjectURL(audioBlob);
const audio = new Audio(audioUrl);
const play = () => {
audio.play();
};

resolve({ audioBlob, audioUrl, play });
});

mediaRecorder.stop();
});
};

resolve({ start, stop });
}).catch(err=>{
const errMsg = err.toString();
console.warn(`Starting audio recording failed with error - ${errMsg}`)
const audioInput = document.getElementById(`${cid}-audio-input`);
audioInput.disabled = true;
});
});
};

// Recorder instance
let recorder = null;


/**
* Adds event listener for audio recording
* @param conversationData: conversation data object
*/
async function addRecorder(conversationData) {

const cid = conversationData["_id"];

const recorderButton = document.getElementById(`${cid}-audio-input`);

if (!recorderButton.disabled) {
recorderButton.onmousedown = async function () {
recorder = await recordAudio(cid);
recorder.start();
};

recorderButton.onmouseup = async function () {
if (recorder) {
recorder.stop().then(audio => {
const audioBlob = toBase64(audio['audioBlob']);
console.log('audioBlob=', audioBlob);
return audioBlob;
}).then(encodedAudio => {
emitUserMessage(encodedAudio, conversationData['_id'], null, [], '1', '0');
});
}
};
}
}/**
* Renders suggestions HTML
*/
async function renderSuggestions() {
const displayedCids = Object.values(await retrieveItemsLayout(true)).join(',');
await fetchServer(`chat_api/get_popular_cids?limit=5&search_str=${conversationSearchInput.value}&exclude_items=${displayedCids}`).then(async response => {
const items = await response.json();
importConversationModalSuggestions.innerHTML = "";
for (const item of Array.from(items)) {
importConversationModalSuggestions.insertAdjacentHTML('afterbegin', await buildSuggestionHTML(item['_id'], item['conversation_name']));
}
Array.from(importConversationModalSuggestions.getElementsByClassName('suggestion-item')).forEach(item => {
const cid = item.getAttribute('data-cid');
if (cid) {
item.addEventListener('click', async (e) => {
await displayConversation(cid);
conversationSearchInput.value = "";
importConversationModal.modal('hide');
// importConversationModalSuggestions.innerHTML = "";
});
item.addEventListener('mouseover', (event) => {
item.classList.add('selected')
});
item.addEventListener('mouseleave', (event) => {
item.classList.remove('selected')
});
}
});
importConversationModalSuggestions.style.setProperty('display', 'inherit', 'important');
});
}/**
* Returns current UNIX timestamp in seconds
* @return {number}: current unix timestamp
*/
const getCurrentTimestamp = () => {
return Math.floor(Date.now() / 1000);
}

// Client's timer
// TODO consider refactoring to "timer per component" if needed
let __timer = 0;


/**
* Sets timer to current timestamp
*/
const startTimer = () => {
__timer = Date.now();
}

/**
* Resets times and returns time elapsed since invocation of startTimer()
* @return {number} Number of seconds elapsed
*/
const stopTimer = () => {
const timeDue = Date.now() - __timer;
__timer = 0;
return timeDue;
};const currentUserNavDisplay = document.getElementById('currentUserNavDisplay');

const logoutModal = $('#logoutModal');

const logoutConfirm = document.getElementById('logoutConfirm');

const loginModal = $('#loginModal');

const loginButton = document.getElementById('loginButton');
const loginUsername = document.getElementById('loginUsername');
const loginPassword = document.getElementById('loginPassword');
const toggleSignup = document.getElementById('toggleSignup');


const signupModal = $('#signupModal');

const signupButton = document.getElementById('signupButton');
const signupUsername = document.getElementById('signupUsername');
const signupFirstName = document.getElementById('signupFirstName');
const signupLastName = document.getElementById('signupLastName');
const signupPassword = document.getElementById('signupPassword');
const repeatSignupPassword = document.getElementById('repeatSignupPassword');
const toggleLogin = document.getElementById('toggleLogin');

let currentUser = null;

/**
* Gets user data from chat client URL
* @param userID: id of desired user (current user if null)
* @returns {Promise<{}>} promise resolving obtaining of user data
*/
async function getUserData(userID=null){
let userData = {}
let query_url = `users_api/`;
if(userID){
query_url+='?user_id='+userID;
}
await fetchServer(query_url)
.then(response => response.ok?response.json():{'data':{}})
.then(data => {
userData = data['data'];
const oldToken = getSessionToken();
if (data['token'] !== oldToken && !userID){
setSessionToken(data['token']);
}
});
return userData;
}

/**
* Method that handles fetching provided user data with valid login credentials
* @returns {Promise<void>} promise resolving validity of user-entered data
*/
async function loginUser(){
const loginModalBody = document.getElementById('loginModalBody');
const query_url = `auth/login/`;
const formData = new FormData();
const inputValues = [loginUsername.value, loginPassword.value];
if(inputValues.includes("") || inputValues.includes(null)){
displayAlert(loginModalBody,'Required fields are blank', 'danger');
}else {
formData.append('username', loginUsername.value);
formData.append('password', loginPassword.value);
await fetchServer(query_url, REQUEST_METHODS.POST,formData)
.then(async response => {
return {'ok':response.ok,'data':await response.json()};
})
.then(async responseData => {
if (responseData['ok']) {
setSessionToken(responseData['data']['token']);
}else{
displayAlert(loginModalBody, responseData['data']['msg'], 'danger', 'login-failed-alert');
loginPassword.value = "";
}
}).catch(ex=>{
console.warn(`Exception during loginUser -> ${ex}`);
displayAlert(loginModalBody);
});
}
}

/**
* Method that handles logging user out
* @returns {Promise<void>} promise resolving user logout
*/
async function logoutUser(){
const query_url = `auth/logout/`;
await fetchServer(query_url).then(async response=>{
if (response.ok) {
const responseJson = await response.json();
setSessionToken(responseJson['token']);
}
});
}

/**
* Method that handles fetching provided user data with valid sign up credentials
* @returns {Promise<void>} promise resolving validity of new user creation
*/
async function createUser(){
const signupModalBody = document.getElementById('signupModalBody');
const query_url = `auth/signup/`;
const formData = new FormData();
const inputValues = [signupUsername.value, signupFirstName.value, signupLastName.value, signupPassword.value, repeatSignupPassword.value];
if(inputValues.includes("") || inputValues.includes(null)){
displayAlert(signupModalBody,'Required fields are blank', 'danger');
}else if(signupPassword.value!==repeatSignupPassword.value){
displayAlert(signupModalBody,'Passwords do not match', 'danger');
}else {
formData.append('nickname', signupUsername.value);
formData.append('first_name', signupFirstName.value);
formData.append('last_name', signupLastName.value);
formData.append('password', signupPassword.value);
await fetchServer(query_url, REQUEST_METHODS.POST, formData)
.then(async response => {
return {'ok':response.ok,'data':await response.json()}
})
.then(async data => {
if(data['ok']){
setSessionToken(data['data']['token']);
}else{
let errorMessage = 'Failed to create an account';
if(data['data'].hasOwnProperty('msg')){
errorMessage = data['data']['msg'];
}
displayAlert(signupModalBody,errorMessage, 'danger');
}
});
}
}

/**
* Helper method for updating navbar based on current user property
* @param forceUpdate to force updating of navbar (defaults to false)
*/
function updateNavbar(forceUpdate=false){
if(currentUser || forceUpdate){
if(currentUserNavDisplay) {
let innerText = currentUser['nickname'];
if(currentUser['is_tmp']){
innerText+=', Login';
}else{
innerText+=', Logout';
}
currentUserNavDisplay.innerHTML = `<a class="nav-link" href="#" style="color: #fff">
${innerText}
</a>`;
}
}
}

/**
* Custom Event fired on current user loaded
* @type {CustomEvent<string>}
*/
const currentUserLoaded = new CustomEvent("currentUserLoaded", { "detail": "Event that is fired when current user is loaded" });

/**
* Convenience method encapsulating refreshing page view based on current user
* @param refreshChats: to refresh the chats (defaults to false)
* @param conversationContainer: DOM Element representing conversation container
*/
async function refreshCurrentUser(refreshChats=false, conversationContainer=null){
await getUserData().then(data=>{
currentUser = data;
console.log(`Loaded current user = ${JSON.stringify(currentUser)}`);
updateNavbar();
if(refreshChats) {
refreshChatView(conversationContainer);
}
console.log('current user loaded');
document.dispatchEvent(currentUserLoaded);
});
}


document.addEventListener('DOMContentLoaded', (e)=>{
if (configData['client'] === CLIENTS.MAIN) {
// document.addEventListener('configLoaded', (e)=>{
//     refreshCurrentUser(true, false);
// });
currentUserNavDisplay.addEventListener('click', (e) => {
e.preventDefault();
currentUser['is_tmp']?loginModal.modal('show'):logoutModal.modal('show');
});

logoutConfirm.addEventListener('click', (e) => {
e.preventDefault();
logoutUser().catch(err => console.error('Error while logging out user: ', err));
});

toggleLogin.addEventListener('click', (e) => {
e.preventDefault();
signupModal.modal('hide');
loginModal.modal('show');
});

loginButton.addEventListener('click', (e) => {
e.preventDefault();
loginUser().catch(err => console.error('Error while logging in user: ', err));
});

toggleSignup.addEventListener('click', (e) => {
e.preventDefault();
loginModal.modal('hide');
signupModal.modal('show');
});

signupButton.addEventListener('click', (e) => {
e.preventDefault();
createUser().catch(err => console.error('Error while creating a user: ', err));
});
}
});

const configNanoLoadedEvent = new CustomEvent("configNanoLoaded", { "detail": "Event that is fired when nano configs are loaded" });

/**
 * Single class that builds embeddable JS widget into the desired website
 */
class NanoBuilder {

    requiredProperties = ['CHAT_DATA', 'CHAT_SERVER_URL_BASE'];
    propertyHandlers = {
        'SOCKET_IO_SERVER_URL': this.resolveSIO,
        'CHAT_SERVER_URL_BASE': this.addConfig,
        'CHAT_CLIENT_URL_BASE': this.setClientURL
    }
    /**
     * Constructing NanoBuilder instance
     * @param options: JS Object containing list of properties for built conversation
     */
    constructor(options) {
        /**
         * Attributes for options:
         * - CHAT_DATA: array of chat configs of type:
         *      {
         *           PARENT_ID: id of parent Node (required)
         *           CID: id of desired conversation (required)
         *      }
         * - SOCKET_IO_SERVER_URL: HTTP Endpoint of Socket IO Server
         * - CHAT_SERVER_URL_BASE: HTTP Endpoint for Klatchat Server
         * - CHAT_CLIENT_URL_BASE: HTTP Endpoint for Klatchat Client
         */
        this.options = options;
        this.options.SOCKET_IO_SERVER_URL = options.SOCKET_IO_SERVER_URL || options.CHAT_SERVER_URL_BASE;
        configData.client = CLIENTS.NANO;
        this.applyConfigs();
        fetchSupportedLanguages()
            .then(async _ => await refreshCurrentUser(false))
            .then(_=>this.resolveChatData(this.options))
            .then(async _=> await requestChatsLanguageRefresh());
    }

    /**
     * Applies configuration params based on declared handlers in "propertyHandlers"
     */
    applyConfigs(){
        this.requiredProperties.forEach(property => {
           if(!this.options.hasOwnProperty(property)){
               throw `${property} is required for NanoBuilder`;
           }
        });
        for (const [key, value] of Object.entries(this.options)) {
            if(this.propertyHandlers.hasOwnProperty(key)){
                const handler = this.propertyHandlers[key];
                if ([this.addConfig, this.setClientURL].includes(handler)){
                    handler(key, value);
                }
                else {
                    this.propertyHandlers[key](this.options);
                }
            }
        }
    }

    /**
     * Resolves nano conversation ID based on options
     * @param options: provided nano builder options
     */
    resolveChatData(options){
        const chatData = options['CHAT_DATA'];
        Array.from(chatData).forEach(chat => {
            getConversationDataByInput(chat['CID']).then(async conversationData=>{
            if(conversationData) {
                await buildConversation(conversationData, CONVERSATION_SKINS.BASE, false, chat['PARENT_ID']);
            }else{
                console.error(`No conversation found matching provided id: ${chat['CID']}`);
            }
        }).catch(err=> console.error(err));
        })
    }

    /**
     * Resolves SIO properties based on provided options
     * @param options: provided nano builder options
     */
    resolveSIO(options){
        configData['SOCKET_IO_SERVER_URL'] = options.SOCKET_IO_SERVER_URL;
        document.dispatchEvent(configNanoLoadedEvent);
    }

    /**
     * Adds config to configData
     * @param key: key to add
     * @param value: value to add under @param key
     */
    addConfig(key, value){
        configData[key] = value;
    }

    setClientURL(key, value){
        configData['currentURLBase'] = value;
    }
}

const initKlatChat = (options) => {
    document.addEventListener('DOMContentLoaded', (e)=>{
        return new NanoBuilder(options);
    })
};