const DATABASES = {
    CHATS: 'chats'
}
const DB_TABLES = {
    CHAT_ALIGNMENT: 'chat_alignment',
    MINIFY_SETTINGS: 'minify_settings',
    CHAT_MESSAGES_PAGINATION: 'chat_messages_pagination'
}
const __db_instances = {}
const __db_definitions = {
    [DATABASES.CHATS]: {
        [DB_TABLES.CHAT_ALIGNMENT]: `cid, added_on, skin`,
        [DB_TABLES.CHAT_MESSAGES_PAGINATION]: `cid, oldest_created_on`
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


class DBGateway {
    constructor(db, table) {
        this.db = db;
        this.table = table;

        this._db_instance = getDb(this.db, this.table);
        this._db_columns_definitions = __db_definitions[this.db][this.table]
        this._db_key = this._db_columns_definitions.split(',')[0]
    }

    async getItem(key = "") {
        return await this._db_instance.where( {[this._db_key]: key} ).first();
    }

    async listItems(orderBy="") {
        let expression = this._db_instance;
        if (orderBy !== ""){
            expression = expression.orderBy(orderBy)
        }
        return await expression.toArray();
    }

    async putItem(data = {}){
        return await this._db_instance.put(data, [data[this._db_key]])
    }

    updateItem(data = {}) {
        const key = data[this._db_key]
        delete data[this._db_key]
        return this._db_instance.update(key, data);
    }

    async deleteItem(key = "") {
        return await this._db_instance.where({[this._db_key]: key}).delete();
    }

    static getInstance(table){
        return new DBGateway(DATABASES.CHATS, table);
    }
}
