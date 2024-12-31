//#region GET functions
///////////////////////////////////////////
//             GET FUNCTIONS             //
///////////////////////////////////////////

// modes (list)
async function getModes() {
    console.debug("running getModes...")

    // send request
    const response = await fetch('/api/get/modes');
    const modes = await response.json();
    
    // empty dropdown
    const dropdown = document.getElementById('dropdown-mode-select');
    dropdown.innerHTML = "";
    
    // populate dropdown
    modes.forEach(mode => {
        let optgroup = dropdown.querySelector(`optgroup[label="${mode[0]}"]`);
        if (!optgroup) {
            optgroup = document.createElement('optgroup');
            optgroup.label = mode[0];
            dropdown.appendChild(optgroup);
        }
        const option = document.createElement('option');
        option.value = modes.indexOf(mode);
        option.textContent = mode[1];
        optgroup.appendChild(option);
    });

    console.debug("finished getModes!")
}

// settings (selected mode, brightness, and sleep times)
async function getSettings(onPageLoad) {
    if (onPageLoad) { console.debug("running getSettings onPageLoad=true...") }
    else { console.debug("running getSettings onPageLoad=false...") }

    // restart button (to colour it)
    const restartbutton = document.getElementById('button-reload-service');

    try {
        // send request
        const response = await fetch('/api/get/settings');
        const data = await response.json();

        // by this point we've had a response so the button can stay green
        restartbutton.classList.toggle('on', true)
        restartbutton.classList.toggle('off', false)
        
        // set values (current mode text)
        document.getElementById("text-mode-select").textContent = `Current Mode: ${data.currentModeDescription}`;
        
        // set values (brightness slider & value text)
        document.getElementById("slider-brightness").value = data.brightness;
        document.getElementById("text-brightness").textContent = `${data.brightness}%`;
        
        // set values (led on/off button colour)
        const ledbutton = document.getElementById('button-led-toggle');
        ledbutton.classList.toggle('on', data.power);
        ledbutton.classList.toggle('off', !(data.power));
        
        // some data should only be loaded on page load (ie dropdown selection and sleep times) so it's possible to edit them without being under a 2s time limit
        if (onPageLoad) {

            // set values (modes dropdown currently selected)
            document.getElementById("dropdown-mode-select").value = data.selectedMode;
            
            // set values (sleep times)
            document.getElementById("time-sleep-weekdays-start").value = data.sleepTimes.weekdays.startTime;
            document.getElementById("time-sleep-weekdays-end").value = data.sleepTimes.weekdays.endTime;
            document.getElementById("time-sleep-weekends-start").value = data.sleepTimes.weekends.startTime;
            document.getElementById("time-sleep-weekends-end").value = data.sleepTimes.weekends.endTime;
        }
        console.debug("finished getSettings!")
    }
    catch (error) {
        restartbutton.classList.toggle('off', true)
        restartbutton.classList.toggle('on', false)
        console.error("getSettings failed!!", error)
        console.error("if you've just restarted the service or the host device, then this could be expected.")
    }
}

// system info
async function getSystemInfo() {
    console.debug("running getSystemInfo...")
    try {

        // send request
        const response = await fetch('/api/get/system-info');
        const data = await response.json();

        // update texts
        document.getElementById('sys-system-uptime').textContent = `Uptime: ${data.uptime}`;
        document.getElementById('sys-cpu-temperature').textContent = `CPU Temperature: ${data.cpuTemperature}°C`;
        document.getElementById('sys-device-info').textContent = `Device: ${data.device}`;
        document.getElementById('sys-current-time').textContent = `Local time: ${data.currentTime}`;

        console.debug("finished getSystemInfo!")

    } catch (error) {
        console.error("getSystemInfo failed!!", error)
        console.error("if you've just restarted the service or the host device, then this could be expected.")
    }
}

//#endregion
//#region AutoLoad Data

// LOAD DATA FROM PYTHON on interval (2s)
setInterval(async () => {
    console.debug("2s check running now")
    getSettings(onPageLoad=false);
    getSystemInfo();
}, 2000);

// LOAD DATA FROM PYTHON on page load
window.onload = function() {
    console.debug("page load started...")
    getSettings(onPageLoad=true);
    getSystemInfo();
    getModes();
    console.debug("finished page load!!")
};




//#endregion
//#region POST functions
////////////////////////////////////////////
//             POST FUNCTIONS             //
////////////////////////////////////////////

// set brightness
let debounceTimeout;
document.getElementById('slider-brightness').addEventListener('input', (event) => {
    console.debug("recieved new brightness input...")
    
    // update % text immediately
    const brightness = event.target.value;
    document.getElementById("text-brightness").textContent = `${brightness}%`;
    
    // send update only when inactive for .3s
    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(async () => {
        console.debug("POSTING new brightness...")
        
        // send request
        await fetch('/api/post/new-brightness', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ brightness: brightness })
        });
        
        console.debug("finished posting new brightness!!")
    }, 300);
});

// set current mode
document.getElementById('button-mode-select').addEventListener('click', async () => {
    console.debug("POSTING new mode...")
    
    // send request
    await fetch('/api/post/new-mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected: parseInt(document.getElementById('dropdown-mode-select').value) })
    });
    
    console.debug("finished posting new mode!!")
});

// set sleep times
document.getElementById('button-sleep-times').addEventListener('click', async () => {
    console.debug("POSTING sleep times...")
    
    // send request
    await fetch('/api/post/new-sleep-times', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            weekdays: {
                startTime: document.getElementById('time-sleep-weekdays-start').value,
                endTime: document.getElementById('time-sleep-weekdays-end').value
            },
            weekends: {
                startTime: document.getElementById('time-sleep-weekends-start').value,
                endTime: document.getElementById('time-sleep-weekends-end').value
            }
        })
    });
    console.debug("finished posting sleep times!!")
});

// toggle power
document.getElementById('button-led-toggle').addEventListener('click', async () => {
    console.debug("POSTING power toggle message...")
    
    // send request
    const response = await fetch('/api/post/toggle-power', { method: 'POST' });
    const data = await response.json();
    
    console.debug("finished posting power toggle message!!")
});

// restart service
document.getElementById('button-reload-service').addEventListener('click', async () => {
    console.log("POSTING restart message. you won't recieve a 'complete' log for this.")
    
    // networkerror occurs since the matching python function restarts the service before it can respond to the request
    // hence the request is then never answered
    console.error("you can safely ignore this error, and the following NetworkError.")
    
    // make button red
    const restartbutton = document.getElementById('button-reload-service');
    restartbutton.classList.toggle('on', false)
    restartbutton.classList.toggle('off', true)
    
    // send request
    fetch('/api/post/restart-service', {
        method: 'POST'
    });
});




//#endregion
//#region LOCAL functions
///////////////////////////////////////////
//            LOCAL FUNCTIONS            //
///////////////////////////////////////////

// refresh page button
document.getElementById('button-reload-page').addEventListener('click', async () => {
    console.warn("reloading page...")
    location.reload()
})
