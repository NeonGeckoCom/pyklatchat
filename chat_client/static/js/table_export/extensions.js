/**
 * Allows for exporting multi sheet with ExportTable module
 * @param exportTable: ExportTables object
 * @param tables: list of tables to export
 * @param mime: mime type
 * @param filename: name of the file to spawn
 * @param sheetNames: array of correspondent sheet names
 * @param extension: type of file extension to use (xls or xlsx)
 * @param merges: mapping of sheet name to merged tables (optional)
 * @param cols_width: mapping of sheet name to column width (optional)
 */
function exportMultiSheet(exportTable, tables, mime, filename, sheetNames, extension, merges = {}, cols_width = {}) {

    const key = extension.substring(1);

    // create workbook
    const wb = new exportTable.Workbook();
    // create sheet for each table in the same page, and add all sheets to workbook
    for (let i = 0; i < tables.length; i++) {
        const sheetName = sheetNames.length - 1 < i ? `Sheet${i}`: shrinkToFit(sheetNames[i], 15, '');
        wb.SheetNames.push(exportTable.escapeHtml(sheetName));
        wb.Sheets[sheetName] = exportTable.createSheet(tables[i], merges[sheetName] || [], cols_width[sheetName] || []);
    }
    const bookType = exportTable.getBookType(key);
    const wopts = {
            bookType: bookType,
            bookSST: false,
            type: 'binary'
        }
    const sheet_data = exportTable.string2ArrayBuffer(XLSX.write(wb, wopts));

    if (sheet_data) {
        saveAs(new Blob([sheet_data],
            {type: mime + ';' + exportTable.charset}),
            filename + extension, true);
    }
}