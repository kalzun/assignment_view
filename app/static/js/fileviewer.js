window.addEventListener('DOMContentLoaded',function () {
    const buttons = document.querySelectorAll(".button");
    buttons.forEach(function(button) {
        button.addEventListener("click", tempStoreFeedback);
    });
    loadTempStoredFeedback();
    // Show files
    const filespanel = document.querySelector("#files-panel");
    showFiles(filespanel);
});
