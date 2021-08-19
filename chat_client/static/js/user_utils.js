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

async function getUserData(userID=null){
    let userData = {}
    let query_url = `${configData["currentURLBase"]}/users/`
    if(userID){
        query_url+='?user_id='+userID;
    }
    await fetch(query_url)
            .then(response => response.ok?response.json():{'data':{}})
            .then(data => {
                userData = data['data'];
            });
     return userData;
}

async function loginUser(){
    const query_url = `${configData["currentURLBase"]}/auth/login/`;
    const formData = new FormData();
    const inputValues = [loginUsername.value, loginPassword.value];
    if(inputValues.includes("") || inputValues.includes(null)){
        displayAlert('loginModalBody','Required fields are blank', 'danger');
    }else {
        formData.append('username', loginUsername.value);
        formData.append('password', loginPassword.value);
        await fetch(query_url, {method:'post', body:formData})
            .then(response => response.ok?response.json():null)
            .then(data => {
                if(data){
                    refreshCurrentUser(false);
                    loginUsername.value = "";
                    loginPassword.value = "";
                    loginModal.modal('hide');
                }
            });
    }
}

async function logoutUser(){
    const query_url = `${configData["currentURLBase"]}/auth/logout/`;
    await fetch(query_url).then(response=>{
        response.ok?refreshCurrentUser(false):'';
        logoutModal.modal('hide');
    });
}

async function createUser(){
    const query_url = `${configData["currentURLBase"]}/auth/signup/`;
    const formData = new FormData();
    const inputValues = [signupUsername.value, signupFirstName.value, signupLastName.value, signupPassword.value, repeatSignupPassword.value];
    if(inputValues.includes("") || inputValues.includes(null)){
        displayAlert('signupModalBody','Required fields are blank', 'danger');
    }else if(signupPassword.value!==repeatSignupPassword.value){
        displayAlert('signupModalBody','Passwords do not match', 'danger');
    }else {
        formData.append('nickname', signupUsername.value);
        formData.append('first_name', signupFirstName.value);
        formData.append('last_name', signupLastName.value);
        formData.append('password', signupPassword.value);
        await fetch(query_url, {method:'post', body:formData})
            .then(async response => {
                return {'ok':response.ok,'data':await response.json()}
            })
            .then(data => {
                if(data['ok']){
                    refreshCurrentUser(false);
                    signupUsername.value = "";
                    signupFirstName.value = "";
                    signupLastName.value = "";
                    signupPassword.value = "";
                    repeatSignupPassword.value = "";
                    signupModal.modal('hide');
                }else{
                    let errorMessage = 'Failed to create an account';
                    if(data['data'].hasOwnProperty('detail')){
                        errorMessage = data['data']['detail'];
                    }
                    displayAlert('signupModalBody',errorMessage, 'danger');
                }
            });
    }
}

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

const currentUserLoaded = new CustomEvent("currentUserLoaded", { "detail": "Event that is fired when current user is loaded" });

function refreshCurrentUser(sendNotification=false){
    getUserData().then(data=>{
        currentUser = data;
        if(sendNotification) {
            document.dispatchEvent(currentUserLoaded);
        }
        updateNavbar();
    });
}


document.addEventListener('DOMContentLoaded', (e)=>{
    refreshCurrentUser(true);
    currentUserNavDisplay.addEventListener('click', (e)=>{
        e.preventDefault();
        if(currentUser['is_tmp']){
            loginModal.modal('show');
        }else{
            logoutModal.modal('show');
        }
    });

    logoutConfirm.addEventListener('click', (e)=>{
        e.preventDefault();
        logoutUser().catch(err=>console.error('Error while logging out user: ',err));
    });

    toggleLogin.addEventListener('click', (e)=>{
        e.preventDefault();
        signupModal.modal('hide');
        loginModal.modal('show');
    });

    loginButton.addEventListener('click', (e)=>{
        e.preventDefault();
        loginUser().catch(err=>console.error('Error while logging in user: ',err));
    });

    toggleSignup.addEventListener('click', (e)=>{
        e.preventDefault();
        loginModal.modal('hide');
        signupModal.modal('show');
    });

    signupButton.addEventListener('click', (e)=>{
        e.preventDefault();
        createUser().catch(err=>console.error('Error while creating a user: ',err));
    });


});