var countElement = document.querySelector('.count')

var currentURL2 = null

if(document.location.pathname == '/') {
    currentURL2 = '/art/all/count'
} else if(document.location.pathname == '/search') {
    currentURL2 = '/search_json/count' + document.location.search
}

fetch(currentURL2)
.then(response => response.json())
.then(count => countElement.innerHTML = `${count} in total`)