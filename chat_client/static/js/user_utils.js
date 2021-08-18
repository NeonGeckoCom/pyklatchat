const currentUserNavDisplay = document.getElementById('currentUserNavDisplay');
const toggleSignup = document.getElementById('toggleSignup');

const loginModal = $('#loginModal');
const signupModal = $('#signupModal');


let currentUser = null;

async function get_user_data(userID=null){
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
    get_user_data().then(data=>{
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
        if(currentUser['is_tmp']){
            loginModal.modal('show');
        }
    });
    toggleSignup.addEventListener('click', (e)=>{
        loginModal.modal('hide');
        signupModal.modal('show');
    });
});