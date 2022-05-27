/**
 * Object representing loaded HTML components mapping:
 * - key: component name,
 * - value: HTML template that should be populated with actual data)
 * @type Object
 */
let loadedComponents = {}

/**
 * Fetches template context into provided html template
 * @param html: HTML template
 * @param templateContext: object containing context to fetch
 * @return {string} HTML with fetched context
 */
function fetchTemplateContext(html, templateContext){
    for (const [key, value] of Object.entries(templateContext)) {
        html = html.replaceAll('{'+key+'}', value);
    }
    return html;
}

/**
 * Builds HTML from passed params and template name
 * @param templateName: name of the template to fetch
 * @param templateContext: properties from template to fetch
 * @returns built template string
 */
async function buildHTMLFromTemplate(templateName, templateContext = {}){
    if(!configData['DISABLE_CACHING'] && loadedComponents.hasOwnProperty(templateName)){
        const html = loadedComponents[templateName];
        return fetchTemplateContext(html, templateContext);
    }else {
        return await fetch(`${configData['CHAT_SERVER_URL_BASE']}/components/${templateName}`)
            .then((response) => {
                if (response.ok) {
                    return response.text();
                }
                throw `template unreachable (HTTP STATUS:${response.status}: ${response.statusText})`
            })
            .then((html) => {
                if (!(configData['DISABLE_CACHING'] || loadedComponents.hasOwnProperty(templateName))) {
                    loadedComponents[templateName] = html;
                }
                return fetchTemplateContext(html, templateContext);
            }).catch(err => console.warn(`Failed to fetch template for ${templateName}: ${err}`));
    }
}


/**
 * Get Node id based on language key
 * @param key: language key (e.g. 'en')
 * @return {string} ID of Node
 */
function getLangOptionID(key){
    return `language-option-${key}`;
}

/**
 * Build language selection HTML based on provided params
 * @param key: language key (e.g 'en')
 * @param name: name of the language (e.g. English)
 * @param icon: language icon (refers to flag-icon specs)
 * @return {string} formatted langSelectPattern
 */
async function buildLangOptionHTML(key, name, icon){
    return await buildHTMLFromTemplate('lang_option', {
        'itemId': getLangOptionID(key),
        'key': key,
        'name': name,
        'icon': icon
    })
}
