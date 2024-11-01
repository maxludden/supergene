document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('chapter-search-form');
    searchForm.addEventListener('submit', function(event) {
        const chapterInput = document.getElementById('chapter-search');
        const chapterNumber = chapterInput.value;

        if (!Number.isInteger(Number(chapterNumber)) || Number(chapterNumber) < 1) {
            event.preventDefault();
            alert('Please enter a valid chapter number.');
        }
    });
});
