/**
 * Returns current UNIX timestamp in seconds
 * @return {number}: current unix timestamp
 */
const getCurrentTimestamp = () => {
    return Math.floor(Date.now() / 1000);
};

// Client's timer
// TODO consider refactoring to "timer per component" if needed
let __timer = 0;


/**
 * Sets timer to current timestamp
 */
const startTimer = () => {
    __timer = Date.now();
};

/**
 * Resets times and returns time elapsed since invocation of startTimer()
 * @return {number} Number of seconds elapsed
 */
const stopTimer = () => {
    const timeDue = Date.now() - __timer;
    __timer = 0;
    return timeDue;
};
