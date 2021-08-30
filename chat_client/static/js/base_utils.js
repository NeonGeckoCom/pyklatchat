function displayAlert(parent_id,text='Error Occurred',alert_type='danger',alert_id='alert'){
    if(!['info','success','warning','danger','primary','secondary','dark'].includes(alert_type)){
        alert_type = 'danger'; //default
    }
    let alert = document.getElementById(alert_id);
    if(alert){
        alert.remove();
    }

    if(text) {
        const container = document.getElementById(parent_id);
        container.insertAdjacentHTML('afterbegin',
            `<div class="alert alert-${alert_type} alert-dismissible" role="alert" id="${alert_id}">
                    <b>${text}</b>
                    <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                        <span aria-hidden="true">&times;</span>
                    </button>
                  </div>`);
    }
}

function generateUUID() {
    const a = crypto.getRandomValues(new Uint16Array(8));
    let i = 0;
    return '00-0-4-1-000'.replace(/[^-]/g,
            s => (a[i++] + s * 0x10000 >> s).toString(16).padStart(4, '0')
    );
}