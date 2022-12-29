/**
 * Enum of possible Alert Behaviours:
 * - DEFAULT: static alert message appeared with no expiration time
 * - AUTO_EXPIRE: alert message will be expired after some amount of time (defaults to 3 seconds)
 */
const alertBehaviors = {
    STATIC: 'static',
    AUTO_EXPIRE: 'auto_expire'
}

/**
 * Adds Bootstrap alert HTML to specified element's id
 * @param parentElem: DOM Element in which to display alert
 * @param text: Text of alert (defaults 'Error Occurred')
 * @param alertType: Type of alert from bootstrap-supported alert types (defaults to 'danger')
 * @param alertID: Id of alert to display (defaults to 'alert')
 * @param alertBehaviorProperties: optional properties associated with alert message behavior
 */
function displayAlert(parentElem,text='Error Occurred',alertType='danger',alertID='alert',
                      alertBehaviorProperties=null){
    if (!parentElem){
        console.warn('Alert is not displayed as parentElem is not defined');
        return
    }
    if (typeof parentElem === 'string'){
        parentElem = document.getElementById(parentElem);
    }
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
        if (alertBehaviorProperties){
           setDefault(alertBehaviorProperties, 'type', alertBehaviors.STATIC);
           if (alertBehaviorProperties['type'] === alertBehaviors.AUTO_EXPIRE){
               const expirationTime = setDefault(alertBehaviorProperties, 'expiration', 3000);
               const slideLength = setDefault(alertBehaviorProperties, 'fadeLength', 500);
               setTimeout(function() {
                    $(`#${alertID}`).slideUp(slideLength, () => {
                        $(this).remove();
                    });
                }, expirationTime);
           }
        }
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
 * @param suffix: suffix to apply after shrunk string
 * @returns {string} Shrunk text, fitting into "maxLength"
 */
function shrinkToFit(text, maxLength, suffix='...'){
    if(text.length>maxLength){
        text = text.substring(0, maxLength) + suffix;
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

/**
 * Fetches URL with no-cors mode
 * @param url: URL to fetch
 * @param properties: request properties
 * @return {Promise<Response>}: Promise of fetching
 */
function fetchNoCors(url, properties = {}){
    properties['mode'] = 'no-cors';
    return fetch(url, properties)
}

/**
 * Checks if element is in current viewport
 * @param element: DOM element to check
 * @return {boolean} True if element in current viewport False otherwise
 */
function isInViewport(element) {
    const rect = element.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

/**
 * Sets default value to the object under the specified key
 * @param obj: object to consider
 * @param key: object key to set
 * @param val: default value to set
 */
function setDefault(obj, key, val){
    if(obj){
        obj[key] ??= val;
    }
    return obj[key];
}

/**
 * Aggregates provided array by the key of its elements
 * @param arr: array to aggregate
 * @param key: aggregation key
 */
function aggregateByKey(arr, key){
    const result = {}
    arr.forEach(item=>{
        try {
            const keyValue = item[key];
            delete item[key];
            if (keyValue && !result[keyValue]) {
                result[keyValue] = item;
            }
        }catch (e) {
            console.warn(`item=${item} has no key ${key}`)
        }
    });
    return result;
}

/**
 * Deletes provided element from DOM
 * @param elem: DOM Object to delete
 */
function deleteElement(elem){
    if (elem && elem?.parentElement) return elem.parentElement.removeChild(elem);
}

const MIMES = [
    ["xml","application/xml"],
    ["bin","application/vnd.ms-excel.sheet.binary.macroEnabled.main"],
    ["vml","application/vnd.openxmlformats-officedocument.vmlDrawing"],
    ["data","application/vnd.openxmlformats-officedocument.model+data"],
    ["bmp","image/bmp"],["png","image/png"],
    ["gif","image/gif"],["emf","image/x-emf"],
    ["wmf","image/x-wmf"],["jpg","image/jpeg"],
    ["jpeg","image/jpeg"],["tif","image/tiff"],
    ["tiff","image/tiff"], ["jfif","image/jfif"],["pdf","application/pdf"],
    ["rels","application/vnd.openxmlformats-package.relationships+xml"]];

const IMAGE_EXTENSIONS = MIMES.filter(item => item[1].startsWith('image/')).map(item=>item[0]);
