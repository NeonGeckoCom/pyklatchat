/**
 * Downloads desired content
 * @param content: content to download
 * @param filename: name of the file to download
 * @param contentType: type of the content
 */
function download(content, filename, contentType='application/octet-stream')
{
    if(content) {
        const a = document.createElement('a');
        const blob = new Blob([content], {'type':contentType});
        a.href = window.URL.createObjectURL(blob);
        a.target = 'blank';
        a.download = filename;
        a.click();
        window.URL.revokeObjectURL(content);
    }else{
        console.warn('Skipping downloading as content is invalid')
    }
}

/**
 * Handles error while loading the image data
 * @param image: target image Node
 */
function handleImgError(image) {
    image.parentElement.insertAdjacentHTML('afterbegin',`<p>${image.getAttribute('alt')}</p>`);
    image.parentElement.removeChild(image);
}
