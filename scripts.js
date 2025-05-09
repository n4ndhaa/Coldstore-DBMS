function animateCounter(id, target) {
    let count = 0;
    const element = document.getElementById(id);
    const increment = target / 50;
    const interval = setInterval(() => {
        count += increment;
        if (count >= target) {
            count = target;
            clearInterval(interval);
        }
        element.textContent = Math.round(count);
    }, 20);
}