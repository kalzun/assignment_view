window.addEventListener('DOMContentLoaded',function () {
    buttons = document.querySelectorAll(".button");
    buttons.forEach(function(button) {
        button.addEventListener("click", tempStoreFeedback);
    });
    loadTempStoredFeedback();
});


function createPythonCode() {
    const pythonScript = document.createElement("script");
    const parent = document.getElementById("running");
    pythonScript.type = "text/python";
    pythonScript.append(editor.getValue());
    parent.appendChild(pythonScript);
}

function clearUp() {
    const result = document.getElementById("result-code-ran");
    const previousRun = document.getElementById("running");
    previousRun.textContent = '';
    result.textContent = '';
}

function runCodeInPython() {
    clearUp();
    createPythonCode();
    brython();
}

function copyStudentcode(show = true) {
  /* Get the text field */
  var copyText = document.getElementById("studentcode");
  if (show) {
      /* Select the text field */
      copyText.select();
      copyText.setSelectionRange(0, 99999); /*For mobile devices*/

      /* Copy the text inside the text field */
      document.execCommand("copy");

      /* Alert the copied text */
      <!-- alert("Copied the text: " + copyText.value); -->
      toggleSuccessInfo("info-success-copy-code");
  }
  else {
      return copyText.value; 
  }
} 

function copyStudentsubmission() {
  /* Get the text field */
  const el = document.createElement('textarea');
  el.value = editor.getValue();
  el.setAttribute('readonly', '');
  el.style.position = 'absolute';
  el.style.left = '-9999px';
  document.body.appendChild(el);
  el.select();
  document.execCommand('copy');
  document.body.removeChild(el);

  toggleSuccessInfo("info-success-copy-submission");
} 

function toggleSuccessInfo(elemid){
  document.getElementById(elemid).classList.toggle("invisible");
  let promise = new Promise(function(resolve, reject) {
      setTimeout(() => resolve("done"), 1000);
    });
  promise.then(
      () => {document.getElementById(elemid).classList.toggle("invisible");}
  ); 
}

function tempStoreFeedback() {
    let tmpFeed = feedback.getValue()
    // console.log(tmpFeed);
    localStorage.setItem(copyStudentcode(false), tmpFeed);
}

function loadTempStoredFeedback() {
    // let feedback = document.getElementById("feedback-field");
    rv = localStorage.getItem(copyStudentcode(false));
    if (rv)
        feedback.setValue(rv);
}

