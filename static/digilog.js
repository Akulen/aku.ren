const canvas = document.getElementById('clockCanvas');
const ctx = canvas.getContext('2d');
const speedSlider = document.getElementById('speedSlider');
const speedLabel = document.getElementById('speed-label');
const hourLabel = document.getElementById('hourLabel');

let startTime = Date.now();
const timezoneOffset = new Date().getTimezoneOffset() * 60000;  // Timezone offset in ms
// Adjust startTime to be in local timezone
startTime -= timezoneOffset + 1000*60*60;
let t0 = Date.now();
let speed = 1.0;
let currentTime = 0;
let angle = 0;
const radius = 130;
const updateInterval = 1000 / 25; // 25 updates per second (40ms per update)

// Draw clock
function drawClock() {
    const center = { x: canvas.width / 2, y: canvas.height / 2 };
    const currentSeconds = currentTime / 1000;  // time in seconds

    // Clear the canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    let foreground = 'black';
    let background = 'white';
    const hours = Math.floor(currentTime / (1000 * 60 * 60)) % 24;
    if(hours % 2 == 0) {
        foreground = 'white';
        background = 'black';
    }
    // Draw the clock face
    ctx.beginPath();
    ctx.arc(center.x, center.y, radius, 0, 2 * Math.PI);
    ctx.fillStyle = background;
    ctx.fill();
    ctx.lineWidth = 3;
    ctx.strokeStyle = 'black';
    ctx.stroke();

    // Draw the minute hand as a pie slice
    const minuteAngle = (currentSeconds / 60 % 60) * 6; // 6 degrees per minute
    ctx.beginPath();
    ctx.moveTo(center.x, center.y);
    ctx.arc(center.x, center.y, radius-ctx.lineWidth/2, - Math.PI / 2, - Math.PI / 2 + Math.radians(minuteAngle), true);
    ctx.lineTo(center.x, center.y);
    ctx.fillStyle = foreground;
    ctx.fill();

    // Set global composite operation to 'difference' for XOR effect
    ctx.globalCompositeOperation = 'difference';

    // Update hour
    ctx.font = '150px "Roboto", Monospace';
    ctx.fillStyle = 'white';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(hours, center.x, center.y+18);

    // Reset the global composite operation back to 'source-over'
    ctx.globalCompositeOperation = 'source-over';
}

// Update time based on speed
function updateTime() {
    currentTime = Date.now() - t0;
    currentTime *= speed;
    currentTime += startTime;
    drawClock();
}

// Event listener for the speed slider
speedSlider.addEventListener('input', (e) => {
    speed = parseFloat(e.target.value);
    speedLabel.textContent = `Speed: ${speed.toFixed(1)}x`;
});

// Start the clock and limit updates to 25 times per second
Math.radians = function(degrees) {
    return degrees * Math.PI / 180;
};

setInterval(updateTime, updateInterval);

