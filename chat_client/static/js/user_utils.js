function get_user_data(userID){
    let userData = {}
    fetch(`http://127.0.0.1:8000/users/${userID}`)
        .then(response => response.ok?response.json():{})
        .then(data => userData = data);
    return userData;
}