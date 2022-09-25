const currentUserNavDisplay = document.getElementById('currentUserNavDisplay');

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
    let query_url = `users_api`;
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
 */
async function refreshCurrentUser(refreshChats=false){
    await getUserData().then(data=>{
        currentUser = data;
        console.log(`Loaded current user = ${JSON.stringify(currentUser)}`);
        updateNavbar();
        if(refreshChats) {
            refreshChatView();
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