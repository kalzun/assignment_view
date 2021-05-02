window.addEventListener('DOMContentLoaded', function() {
  const filespanel = document.querySelector("#files-panel");
  showFiles(filespanel);
  // show content of file if any
  const context = document.querySelector("#valid-file");
  if (context) {
    const filename = context.value;
    editor.setValue(localStorage.getItem(filename));
  }
});


function saveFile() {
  filename = document.querySelector("#valid-file").value;
  content = editor.getValue();
  saveFilesIndex(filename);
  localStorage.setItem(filename, content);
}

function deleteFile(fn) {
  const exists = localStorage.getItem(fn);
  if (exists) {
    localStorage.removeItem(fn)
    const files = getFilesIndex();
    const newFiles = [];
    for (let file of files) {
      if (file != fn)
        newFiles.push(file)
    }
    saveFilesIndex(null, newFiles);
  }
  else
    console.log("File not found");
}

function saveFilesIndex(filename, sequence) {
  let files = localStorage.getItem("allFiles")
  if (sequence) {
    files = JSON.stringify(sequence);
  }
  const allFiles = files ? JSON.parse(files) : [];
  if (!sequence)
    if (!allFiles.includes(filename))
      allFiles.push(filename);
  localStorage.setItem("allFiles", JSON.stringify(allFiles));
}

function getFilesIndex() {
  const files = JSON.parse(localStorage.getItem("allFiles"));
  return files;
}

function clearAllFiles() {
  const files = getFilesIndex();
  for (file of files) {
    deleteFile(file);
  }
}

function getFile(filename) {
  return localStorage.getItem(filename);
}

function showFiles(parentTag) {
  const files = getFilesIndex();
  if (!files) {
    return
  }
  const url = new URL(window.location.href);
  while (parentTag.lastChild) {
    parentTag.removeChild(parentTag.lastChild);
  }
  for (let file of files) {
    const child = document.createElement("a");
    child.href = url.origin + "/files/"+ file
    child.classList.add("panel-block");
    child.innerHTML = file;
    parentTag.appendChild(child)
  }

}
