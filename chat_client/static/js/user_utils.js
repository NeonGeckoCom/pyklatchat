const currentUserNavDisplay = document.getElementById('currentUserNavDisplay');
const toggleSignup = document.getElementById('toggleSignup');
const loginButton = document.getElementById('loginButton');
const loginUsername = document.getElementById('loginUsername');
const loginPassword = document.getElementById('loginPassword');

const loginModal = $('#loginModal');
const signupModal = $('#signupModal');


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
        console.error('Blank data provided');
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

function updateNavbar(forceUpdate=false){
    if(currentUser || forceUpdate){
        if(currentUserNavDisplay) {
            let innerText = currentUser['nickname'];
            console.log(currentUser['is_tmp']);
            if(currentUser['is_tmp']){
                innerText+=', Login'
            }else{
                innerText+=', Logout'
            }
            console.log('here')
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
    toggleSignup.addEventListener('click', (e)=>{
        e.preventDefault();
        loginModal.modal('hide');
        signupModal.modal('show');
    });

    loginButton.addEventListener('click', (e)=>{
        e.preventDefault();
        loginUser().catch(err=>console.error('Error while logging in user: ',err));
    });
});