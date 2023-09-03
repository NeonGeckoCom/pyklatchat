/**
 * Gets time object from provided UNIX timestamp
 * @param timestampCreated: UNIX timestamp (in seconds)
 * @returns {string} string time (hours:minutes)
 */
function getTimeFromTimestamp(timestampCreated=0){
    if (!timestampCreated){
        return ''
    }
    let date = new Date(timestampCreated * 1000);
    let year = date.getFullYear().toString();
    let month = date.getMonth()+1;
    month = month>=10?month.toString():'0'+month.toString();
    let day = date.getDate();

    day = day>=10?day.toString():'0'+day.toString();
    const hours = date.getHours().toString();
    let minutes = date.getMinutes();
    minutes = minutes>=10?minutes.toString():'0'+minutes.toString();
    return strFmtDate(year, month, day, hours, minutes, null);
}

/**
 * Composes date based on input params
 * @param year: desired year
 * @param month: desired month
 * @param day: desired day
 * @param hours: num of hours
 * @param minutes: minutes
 * @param seconds: seconds
 * @return date string
 */
function strFmtDate(year, month, day, hours, minutes, seconds){
    let finalDate = "";
    if(year && month && day){
        finalDate+=`${year}-${month}-${day}`
    }
    if(hours && minutes) {
        finalDate += ` ${hours}:${minutes}`
        if (seconds) {
            finalDate += `:${seconds}`
        }
    }
    return finalDate;
}