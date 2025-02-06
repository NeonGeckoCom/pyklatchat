document.addEventListener('configLoaded',async (_)=> {

    const buildVersion = configData?.["BUILD_VERSION"];
    const buildTS = configData?.["BUILD_TS"];
    if (buildVersion && buildTS) {
        document.getElementById("app-version").innerText = `v${buildVersion} (${getTimeFromTimestamp(buildTS)})`;
    }
});