var countElement = document.querySelector('.count')

fetch('/art/all/count')
.then(response => response.json())
.then(count => countElement.innerHTML = `${count} in total`)