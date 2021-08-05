function get_user_data(userID=null){
    let userData = {}
    let query_url = `http://127.0.0.1:8000/users/`
    if(userID){
        query_url+=userID;
    }
    fetch(query_url)
        .then(response => response.ok?response.json():{})
        .then(data => userData = data['data']);
    return userData;
}