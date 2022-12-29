let currentUserNavDisplay = document.getElementById('currentUserNavDisplay');
/* Login items */
let loginModal;
let loginButton;
let loginUsername;
let loginPassword;
let toggleSignup;
/* Logout Items */
let logoutModal;
let logoutConfirm;
/* Signup items */
let signupModal;
let signupButton;
let signupUsername;
let signupFirstName;
let signupLastName;
let signupPassword;
let repeatSignupPassword;
let toggleLogin;

let currentUser = null;


function initModalElements(){
    currentUserNavDisplay = document.getElementById('currentUserNavDisplay');
    logoutModal = $('#logoutModal');
    logoutConfirm = document.getElementById('logoutConfirm');
    loginModal = $('#loginModal');
    loginButton = document.getElementById('loginButton');
    loginUsername = document.getElementById('loginUsername');
    loginPassword = document.getElementById('loginPassword');
    toggleSignup = document.getElementById('toggleSignup');
    signupModal = $('#signupModal');
    signupButton = document.getElementById('signupButton');
    signupUsername = document.getElementById('signupUsername');
    signupFirstName = document.getElementById('signupFirstName');
    signupLastName = document.getElementById('signupLastName');
    signupPassword = document.getElementById('signupPassword');
    repeatSignupPassword = document.getElementById('repeatSignupPassword');
    toggleLogin = document.getElementById('toggleLogin');
}


const MODAL_NAMES = {
    LOGIN: 'login',
    LOGOUT: 'logout',
    SIGN_UP: 'signup',
    USER_SETTINGS: 'user_settings'
}


/**
 * Adds new modal under specific conversation id
 * @param name: name of the modal from MODAL_NAMES to add
 */
async function addModal(name){
    if (Object.values(MODAL_NAMES).includes(name)){
        return await buildHTMLFromTemplate(`modals.${name}`)
    }else{
        console.warn(`Unresolved modal name - ${name}`)
    }
}

/**
 * Initializes modals per target conversation id (if not provided - for main client)
 * @param parentID: id of the parent to attach element to
 */
async function initModals(parentID=null){
    if (parentID) {
        const parentElem = document.getElementById( parentID );
        if (!parentElem) {
            console.warn( 'No element detected with provided parentID=', parentID )
            return -1;
        }
        for (const modalName of [
            MODAL_NAMES.LOGIN,
            MODAL_NAMES.LOGOUT,
            MODAL_NAMES.SIGN_UP,
            MODAL_NAMES.USER_SETTINGS]) {
               const modalHTML = await addModal(modalName);
               parentElem.insertAdjacentHTML('beforeend', modalHTML);
           }
    }
    initModalElements();
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
    const modalsLoaded = new CustomEvent('modalsLoaded');
    document.dispatchEvent(modalsLoaded);
}

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
        let innerText = shrinkToFit(currentUser['nickname'], 10);
        let targetElems = [currentUserNavDisplay];
        if (configData.client === CLIENTS.MAIN){
            if(currentUser['is_tmp']){
                // Leaving only "guest" without suffix
                innerText = innerText.split('_')[0]
                innerText+=', Login';
            }else{
                innerText+=', Logout';
            }
        }else if (configData.client === CLIENTS.NANO){
            if(currentUser['is_tmp']){
                // Leaving only "guest" without suffix
                innerText = innerText.split('_')[0]
                innerText+=' <i class="fa-solid fa-right-to-bracket"></i>';
            }else{
                innerText+=' <i class="fa-solid fa-right-from-bracket"></i>';
            }
            targetElems = Array.from(document.getElementsByClassName('account-link'))
        }
        if(targetElems.length > 0 && targetElems[0]) {
            targetElems.forEach(elem=>{
                elem.innerHTML = `<a class="nav-link" href="#" style="color: #fff" data-toggle="tooltip" title="Authorized as ${currentUser['nickname']}">
                                        ${innerText}
                                   </a>`;
            });
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
        setTimeout( () => updateNavbar(), 500);
        if(refreshChats) {
            refreshChatView(conversationContainer);
        }
        console.log('current user loaded');
        document.dispatchEvent(currentUserLoaded);
        return data;
    });
}



document.addEventListener('DOMContentLoaded', async (e)=>{
    if (configData['client'] === CLIENTS.MAIN) {
        await initModals();
        currentUserNavDisplay.addEventListener('click', (e) => {
            e.preventDefault();
            currentUser['is_tmp']?loginModal.modal('show'):logoutModal.modal('show');
        });
    }
});