const REQUEST_METHODS = {
    GET: 'GET',
    PUT: 'PUT',
    DELETE: 'DELETE',
    POST: 'POST'
}


const fetchServer = async (urlSuffix, method=REQUEST_METHODS.GET, body=null, noCors=false) => {
    const options = {
        method: method,
        headers: new Headers({'Authorization': localStorage.getItem('session') || ''})
    }
    if (noCors){
        options['mode'] = 'no-cors';
    }
    if (body){
        options['body'] = body;
    }
    return fetch(`${configData["CHAT_SERVER_URL_BASE"]}/${urlSuffix}`, options).then(async response => {
        if (response.status === 401){
            const responseJson = await response.json();
            if (responseJson['detail'] === 'Session Expired'){
               location.reload();
            }
        }
        return response;
    });
}