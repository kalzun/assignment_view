async function createPythonCode() {
    const pythonScript = document.createElement("script");
    const parent = document.getElementById("running");
    pythonScript.type = "text/python";

    let pre_py = await getCustomHandler()
    pythonScript.append(pre_py);
    pythonScript.append(editor.getValue());
    parent.appendChild(pythonScript);
}

async function getCustomHandler() {
    const customHandler = document.getElementById("customHandler");
    let response = await fetch("/js/pre_py.py");
    return await response.text();
}

function clearUp() {
    const result = document.getElementById("result-code-ran");
    const previousRun = document.getElementById("running");
    previousRun.textContent = '';
    result.textContent = '';
}

async function runCodeInPython() {
    const orgPrompt = prompt;
    window.prompt = function(msg) {
      const rv = orgPrompt(msg);
      console.log("Scrolling")
      // result.scrollIntoView(false);
      return rv;
    }
    clearUp();
    await createPythonCode();

    // Debuggin
    const running = document.getElementById("running");
    console.log("running")
    console.log(running)


    function footScroll(){
      const footerTag = document.querySelector(".footer")
      footerTag.scrollIntoView(false);
    }

    (function(callback) {
      brython();
      callback();
    })(footScroll);


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
      // alert("Copied the text: " + copyText.value);
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
  let promise = new Promise(function(resolve) {
      setTimeout(() => resolve("done"), 1000);
    });
  promise.then(
      () => {document.getElementById(elemid).classList.toggle("invisible");}
  );
}

function makeKeyForLocalStorage(){
    let code = copyStudentcode(false);
    return `${group_n}_${assignment_id}_${code}`;
}

function tempStoreFeedback() {
    let tmpFeed = feedback.getValue()
    localStorage.setItem(makeKeyForLocalStorage(), tmpFeed);
}

async function fetching_comment(assId, userId){
  let resp = await fetch(`/previous_comments/${assId}/${userId}`);
  let comment = await resp.text()
  feedback.setValue(comment);
}


function loadTempStoredFeedback() {
    // let feedback = document.getElementById("feedback-field");
    rv = localStorage.getItem(makeKeyForLocalStorage());
    console.log("Should return")
    console.log(rv)
    if (rv)
        feedback.setValue(rv);
}

function activateModal(modalId) {
    modal = document.getElementById(modalId);
    modal.classList.add("is-active");
    bg_modal = document.getElementById(modalId + "-bg");
    d_btn_modal = document.getElementById(modalId + "-close-modal");
    bg_modal.addEventListener("click", function() {
        modal.classList.remove("is-active");
    });
    d_btn_modal.addEventListener("click", function() {
        modal.classList.remove("is-active");
    });
}

function getCommentFeedback() {
    // Store it in localstorage:
    tempStoreFeedback();
    let comment = feedback.getValue();
    formInput = document.getElementById("formcomment");
    formInput.value = comment;
}
