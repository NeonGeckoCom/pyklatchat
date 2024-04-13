const DATABASES = {
    CHATS: 'chats'
}
const DB_TABLES = {
    CHAT_ALIGNMENT: 'chat_alignment',
    MINIFY_SETTINGS: 'minify_settings'
}
const __db_instances = {}
const __db_definitions = {
    "chats": {
        "chat_alignment": `cid, added_on, skin`
    }
}

/**
 * Gets database and table from name
 * @param db: database name to get
 * @param table: table name to get
 * @return {Table} Dexie database object under specified table
 */
const getDb = (db, table) => {
    let _instance;
    if (!Object.keys(__db_instances).includes(db)){
        _instance = new Dexie(name);
        if (Object.keys(__db_definitions).includes(db)){
            _instance.version(1).stores(__db_definitions[db]);
        }
        __db_instances[db] = _instance;
    }else{
        _instance = __db_instances[db];
    }
    return _instance[table];
}