const REQUEST_METHODS = {
    GET: 'GET',
    PUT: 'PUT',
    DELETE: 'DELETE',
    POST: 'POST'
}

const controllers = new Set();


const getSessionToken = () => {
    return localStorage.getItem('session') || '';
}

const setSessionToken = (val) => {
    const currentValue = getSessionToken();
    localStorage.setItem( 'session', val );
    if (currentValue && currentValue!==val) {
        location.reload();
    }
}

const fetchServer = async (urlSuffix, method=REQUEST_METHODS.GET, body=null, json=false) => {
    const controller = new AbortController();
    controllers.add(controller);
    const signal = controller.signal;

    const options = {
        method: method,
        headers: new Headers({'Authorization': getSessionToken()}),
        signal,
    }
    if (body){
        options['body'] = body;
    }
    // TODO: there is an issue validating FormData on backend, so JSON property should eventually become true
    if (json){
        options['headers'].append('Content-Type', 'application/json');
        if (options['body']) {
            options['body'] &&= JSON.stringify(options['body'])
        }
    }
    return fetch(`${configData["CHAT_SERVER_URL_BASE"]}/${urlSuffix}`, options).then(async response => {
        if (response.status === 401){
            const responseJson = await response.json();
            if (responseJson['msg'] === 'Session token is invalid or expired'){
                localStorage.removeItem('session');
                location.reload();
            }
        }
        return response;
    }).finally(() => {
        controllers.delete(controller);
    });
}


document.addEventListener('beforeunload', () => {
    for (const controller of controllers) {
        controller.abort();
    }
});
