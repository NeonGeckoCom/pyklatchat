const currentUserNavDisplay = document.getElementById('currentUserNavDisplay');


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
                }
            });
    }
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
        formData.append('nickname', loginUsername.value);
        formData.append('first_name', signupFirstName.value);
        formData.append('last_name', signupLastName.value);
        formData.append('password', loginPassword.value);
        await fetch(query_url, {method:'post', body:formData})
            .then(response => response.ok?response.json():null)
            .then(data => {
                if(data){
                    refreshCurrentUser(false);
                }else{
                    displayAlert('signupModalBody',`Failed to create an account: ${data['detail'][0]['msg']}`, 'danger');
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
        }
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