let currentUser = null;

get_user_data().then(data=>{
    currentUser = data;
});

async function get_user_data(userID=null){
    let userData = {}
    let query_url = `http://127.0.0.1:8001/users/`
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