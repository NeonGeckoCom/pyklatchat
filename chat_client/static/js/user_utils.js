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

function updateNavbar(){
    if(currentUser){
        const currentUserNavDisplay = document.getElementById('currentUserNavDisplay');
        if(currentUserNavDisplay) {
            currentUserNavDisplay.innerHTML = `<li class="nav-item">
                                                <a class="nav-link" href="#" style="color: #fff">
                                                    Logged in as: ${currentUser['nickname']}
                                                </a>
                                            </li>`;
        }
    }
}

const currentUserLoaded = new CustomEvent("currentUserLoaded", { "detail": "Event that is fired when current user is loaded" });


document.addEventListener('DOMContentLoaded', (e)=>{
    get_user_data().then(data=>{
        currentUser = data;
        document.dispatchEvent(currentUserLoaded);
        updateNavbar();
    });
});