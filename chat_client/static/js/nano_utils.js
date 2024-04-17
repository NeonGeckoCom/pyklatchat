/**
 * Displays modal bounded to the provided conversation id
 * @param modalElem: modal to display
 * @param cid: conversation id to consider
 */
function displayModalInCID(modalElem, cid){
    modalElem.modal('hide');
    $('.modal-backdrop').appendTo(`#${cid}`);
    modalElem.modal('show');
}
