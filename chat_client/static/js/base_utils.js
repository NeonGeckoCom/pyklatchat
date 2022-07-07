/**
 * Adds Bootstrap alert HTML to specified element's id
 * @param parentElem: DOM Element in which to display alert
 * @param text: Text of alert (defaults 'Error Occurred')
 * @param alertType: Type of alert from bootstrap-supported alert types (defaults to 'danger')
 * @param alertID: Id of alert to display (defaults to 'alert')
 */
function displayAlert(parentElem,text='Error Occurred',alertType='danger',alertID='alert'){
    if(!['info','success','warning','danger','primary','secondary','dark'].includes(alertType)){
        alertType = 'danger'; //default
    }
    let alert = document.getElementById(alertID);
    if(alert){
        alert.remove();
    }

    if(text) {
        parentElem.insertAdjacentHTML('afterbegin',
            `<div class="alert alert-${alertType} alert-dismissible" role="alert" id="${alertID}">
                    <b>${text}</b>
                    <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                        <span aria-hidden="true">&times;</span>
                    </button>
                  </div>`);
    }
}

/**
 * Generates UUID hex
 * @param length: length of UUID (defaults to 8)
 * @param strPattern: pattern to follow for UUID (optional)
 * @returns {string} Generated UUID hex
 */
function generateUUID(length=8, strPattern='00-0-4-1-000') {
    const a = crypto.getRandomValues(new Uint16Array(length));
    let i = 0;
    return strPattern.replace(/[^-]/g,
            s => (a[i++] + s * 0x10000 >> s).toString(16).padStart(4, '0')
    );
}

/**
 * Shrinks text to fit into desired length
 * @param text: Text to shrink
 * @param maxLength: max length of text to save
 * @returns {string} Shrunk text, fitting into "maxLength"
 */
function shrinkToFit(text, maxLength){
    if(text.length>maxLength){
        text = text.substring(0, maxLength/2) + '...' + text.substring(text.length - maxLength/2, text.length);
    }return text;
}


/**
 * Converts file to base64
 * @param file: desired file
 * @return {Promise}
 */
const toBase64 = file => new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve(reader.result);
    reader.onerror = error => reject(error);
});

/**
 * Extracts filename from path
 * @param path: path to extract from
 */
function getFilenameFromPath(path){
    return path.replace(/.*[\/\\]/, '');
}