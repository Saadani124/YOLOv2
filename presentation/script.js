document.addEventListener('DOMContentLoaded', () => {
    const slides = document.querySelectorAll('.slide');
    const indicatorsContainer = document.getElementById('indicators');
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    let currentSlide = 0;

    // Create indicators
    slides.forEach((_, index) => {
        const indicator = document.createElement('div');
        indicator.classList.add('indicator');
        if (index === 0) indicator.classList.add('active');
        indicator.addEventListener('click', () => goToSlide(index));
        indicatorsContainer.appendChild(indicator);
    });

    const indicators = document.querySelectorAll('.indicator');

    function updateControls() {
        prevBtn.classList.toggle('disabled', currentSlide === 0);
        nextBtn.classList.toggle('disabled', currentSlide === slides.length - 1);
        
        indicators.forEach((ind, i) => {
            ind.classList.toggle('active', i === currentSlide);
        });
    }

    function goToSlide(index) {
        slides[currentSlide].classList.remove('active');
        currentSlide = index;
        slides[currentSlide].classList.add('active');
        updateControls();
    }

    prevBtn.addEventListener('click', () => {
        if (currentSlide > 0) goToSlide(currentSlide - 1);
    });

    nextBtn.addEventListener('click', () => {
        if (currentSlide < slides.length - 1) goToSlide(currentSlide + 1);
    });

    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowLeft' && currentSlide > 0) goToSlide(currentSlide - 1);
        if (e.key === 'ArrowRight' && currentSlide < slides.length - 1) goToSlide(currentSlide + 1);
    });
});