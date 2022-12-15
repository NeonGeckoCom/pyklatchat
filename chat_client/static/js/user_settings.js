let userSettingsModal;
let applyUserSettings;
let minifyMessagesCheck;
let settingsLink;

/**
 * Displays relevant user settings section based on provided name
 * @param name: name of the section to display
 */
const displaySection = (name) => {
    Array.from(document.getElementsByClassName('user-settings-section')).forEach(elem=>{
       elem.hidden = true;
    });
    const elem = document.getElementById(`user-settings-${name}-section`);
    elem.hidden = false;
}

/**
 * Displays user settings based on received preferences
 * @param preferences
 */
const displayUserSettings = (preferences) => {
    if (preferences){
        minifyMessagesCheck.checked = preferences?.minify_messages === '1'
    }
}

/**
 * Initialises section of settings based on provided name
 * @param sectionName: name of the section provided
 */
const initSettingsSection = async (sectionName) => {
    await refreshCurrentUser(false)
        .then(userData=>displayUserSettings(userData?.preferences))
        .then(_=>displaySection(sectionName));
}

/**
 * Initialises User Settings Modal
 */
const initSettingsModal = async () => {
    Array.from(document.getElementsByClassName('nav-user-settings')).forEach(navItem=>{
       navItem.addEventListener('click', async (e)=>{
           await initSettingsSection(navItem.getAttribute('data-section-name'));
       });
    });
}

/**
 * Applies new settings to current user
 */
const applyNewSettings = async () => {
    const formData = new FormData();
    formData.append('minify_messages', minifyMessagesCheck.checked?'1':'0');
    const query_url = 'users_api/settings/update'
    await fetchServer(query_url, REQUEST_METHODS.POST, formData).then(async response => {
        const responseJson = await response.json();
        if (response.ok) {
            location.reload();
        } else {
            displayAlert(document.getElementById(`userSettingsModalBody`),
                `${responseJson['msg']}`,
                'danger');
        }
    });
}

function initSettings(elem){
    elem.addEventListener( 'click', async (e) => {
        await initSettingsModal();
        userSettingsModal.modal('show');
    });
}

/**
 * Initialise user settings links based on the current client
 */
const initSettingsLinks = () => {
    if (configData.client === CLIENTS.NANO) {
        console.log('initialising settings link for ', Array.from( document.getElementsByClassName( 'settings-link' ) ).length, ' elements')
        Array.from( document.getElementsByClassName( 'settings-link' ) ).forEach(elem => {
            initSettings(elem);
        } );
    }else{
        initSettings(document.getElementById('settingsLink'));
    }
}

document.addEventListener('DOMContentLoaded', (_)=>{
    if (configData.client === CLIENTS.MAIN) {
        userSettingsModal = $('#userSettingsModal');
        applyUserSettings = document.getElementById('applyUserSettings');
        minifyMessagesCheck = document.getElementById('minifyMessages');
        applyUserSettings.addEventListener( 'click', async (e) => await applyNewSettings() );
        settingsLink = document.getElementById('settingsLink');
        settingsLink.addEventListener( 'click', async (e) => {
            e.preventDefault();
            await initSettingsModal();
            userSettingsModal.modal( 'show' );
        } );
    }else {
        document.addEventListener( 'modalsLoaded', (e) => {
            userSettingsModal = $( '#userSettingsModal' );
            applyUserSettings = document.getElementById( 'applyUserSettings' );
            minifyMessagesCheck = document.getElementById( 'minifyMessages' );
            applyUserSettings.addEventListener( 'click', async (e) => await applyNewSettings() );
            if (configData.client === CLIENTS.MAIN) {
                initSettingsLinks();
            }
        } );

        document.addEventListener( 'nanoChatsLoaded', (e) => {
            setTimeout( () => initSettingsLinks(), 1000 );
        } )
    }
});
