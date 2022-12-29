const myAccountLink = document.getElementById('myAccountLink');

/**
 * Shows modal associated with profile
 * @param nick: nickname to fetch
 * @param edit: to open modal in edit mode
 *
 * @return true if modal shown successfully, false otherwise
 */
async function showProfileModal(nick=null, edit='0'){
    let fetchURL = `${configData['currentURLBase']}/components/profile?`
    let modalId;
    let avatarId;
    if(edit === '1'){
        modalId = `${currentUser['nickname']}EditModal`;
        // avatarId = `${currentUser['nickname']}EditAvatar`;
        fetchURL += `edit=1`;
    }else{
        modalId = `${nick}Modal`;
        // avatarId = `${nick}Avatar`;
        fetchURL += `nickname=${nick}`;
    }
    const profileModalHTML = await fetch(fetchURL, {headers: new Headers({'Authorization': getSessionToken()})}).then(async (response) => {
        if (response.ok) {
            return await response.text();
        }
        throw `unreachable (HTTP STATUS:${response.status}: ${response.statusText})`
    }).catch(err=> {
        console.warn(err);
        return null;
    });
    if (profileModalHTML){
        const existingModal = document.getElementById(modalId);
        deleteElement(existingModal);
        const main = document.getElementById('main');
        main.insertAdjacentHTML('afterbegin', profileModalHTML);
        const existingModalJQuery = $(`#${modalId}`);
        existingModalJQuery.modal('show');
        return true
    } return false;
}

/**
 * Convenience wrapper to show modal in the edit mode
 */
async function showProfileEditModal(){
    return await showProfileModal(null, '1');
}

/**
 * Previews uploaded image
 * @param nickname: target nickname
 */
const previewFile = (nickname) => {
    const userNewAvatar = document.getElementById(`${nickname}NewAvatar`);
    const userEditAvatar = document.getElementById(`${nickname}EditAvatar`);
    if (userNewAvatar?.files.length > 0) {
        const objectURL = window.URL.createObjectURL(userNewAvatar.files[0]);
        try{
            URL.revokeObjectURL(userEditAvatar.src);
        } catch (e) {
            console.debug('Its initial URL');
        }
        userEditAvatar.src = objectURL;
    }
}

async function initProfileEditModal(){
    const nickname = currentUser['nickname'];
    if (currentUser?.is_tmp){
        loginModal.modal('show');
        return
    }
    const modalShown = await showProfileEditModal().catch(err=>{
                console.warn(`Failed to show edit profile modal - ${err}`);
                return false;
            });
    if (!modalShown) return;
    const editProfileSubmitButton = document.getElementById(`${nickname}EditSubmit`);
    const userNewAvatar = document.getElementById(`${nickname}NewAvatar`);
    const userEditAvatar = document.getElementById(`${nickname}EditAvatar`);
    const logoutButton = document.getElementById('logoutButton');

    editProfileSubmitButton.addEventListener('click', async (e) => {
        e.preventDefault();
        const nick = currentUser['nickname'];
        const nickname = document.getElementById(`${nick}EditNickname`);
        const firstName = document.getElementById(`${nick}EditFirstName`);
        const lastName = document.getElementById(`${nick}EditLastName`);
        const bio = document.getElementById(`${nick}EditBio`);
        const password = document.getElementById(`${nick}EditPassword`);
        const repeatPassword = document.getElementById(`${nick}RepeatEditPassword`);

        const formData = new FormData();

        if (userNewAvatar?.files.length > 0) {
            formData.append('avatar', userNewAvatar.files[0]);
        }
        formData.append('user_id', currentUser['_id']);
        formData.append('nickname', nickname.value);
        formData.append('first_name', firstName.value);
        formData.append('last_name', lastName.value);
        formData.append('bio', bio.value);
        formData.append('password', password.value);
        formData.append('repeat_password', repeatPassword.value);

        const query_url = `users_api/update`;
        await fetchServer(query_url, REQUEST_METHODS.POST, formData).then(async response => {
            const responseJson = await response.json();
            if (response.ok) {
                location.reload();
            } else {
                password.value = "";
                repeatPassword.value = '';
                displayAlert(document.getElementById(`${nick}EditBody`),
                    `${responseJson['msg']}`,
                    'danger');
            }
        });
    });

    userEditAvatar.addEventListener('click', (e)=>{
        e.preventDefault();
        userNewAvatar.click();
    });

    logoutButton.addEventListener('click', (e) => {
        $(`#${currentUser['nickname']}EditModal`).modal('hide');
        logoutModal.modal('show');
    });
}


/**
 * Attaches invoker for current profile edit modal
 * @param elem: target DOM element
 */
function attachEditModalInvoker(elem){
    elem.addEventListener( 'click', async (e) => {
        e.preventDefault();
        await initProfileEditModal();
    });
}


document.addEventListener('DOMContentLoaded', (e) => {

    if (configData.client === CLIENTS.MAIN) {
        attachEditModalInvoker(myAccountLink);
    }
});