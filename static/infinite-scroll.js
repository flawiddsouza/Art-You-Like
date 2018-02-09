var container = document.querySelector('.grid')

const distanceFromEndInPXToStartLoadingNext = 3000

var loading = false

var offset = 51 // starting offset
const count = 51 // amount of items to add

var currentURL = null
if(document.location.pathname == '/') {
    currentURL = '/art/all?'
} else if(document.location.pathname == '/search') {
    currentURL = '/search_json?' + document.location.search + '&'
}


function loadMore() {
    loading = true
    fetch(`${currentURL}count=${count}&offset=${offset}`)
    .then(response => response.json())
    .then(artItems => {
        if(artItems.length == 0) { // this signifies that there are no more entries to be loaded
            return // loading will not be set to false, hence preventing loadMore from being called again
        }
        var artsHTML = ''
        while(artItems.length > 0) {
            var artItemsBatch3 = artItems.splice(0, 3)
            var artHTML = '<div class="columns">'
            artItemsBatch3.forEach(art => {
                var images = ''
                art.image_url.forEach(image_url => {
                    images += `
                        <a class="fullscreen-mode" data-title="{{ art.title }}" data-image-url="/static/images/${image_url}">
                            <img src="data:image/svg+xml;charset=utf-8,%3Csvg xmlns%3D'http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg' viewBox%3D'0 0 200 150'%2F%3E" data-src="/static/images/${image_url}" class="image lozad">
                        </a>
                    `
                })
                if(art.image_url.length == 0) {
                    images = `<div class="has-text-centered">No image is attached to this artwork</div>`
                }
                artHTML += `
                    <div class="column is-one-third">
                        <div class="grid-art-wrapper">
                            <a href="/art/${art.id}">
                                <div class="grid-art-title">${art.title}</div>
                            </a>
                            ${images}
                            <div class="grid-art-by">
                                <h3 class="subtitle">by <a href='/search?q=artist:"${art.artist_name}"'>${art.artist_name}</a> [<a href="${art.artist_website}">Web</a>]</h3>
                            </div>
                        </div>
                    </div>
                `
            })
            artHTML += '</div>'
            artsHTML += artHTML
        }

        container.innerHTML += artsHTML

        // reload lozard
        var observer = lozad()
        observer.observe()

        offset += count

        loading = false
    })
}

window.addEventListener('scroll', (e) => {
    if(loading) {
        return
    }
    // scrolled to the bottom
    if(document.documentElement.scrollHeight - (window.pageYOffset + document.documentElement.clientHeight) < distanceFromEndInPXToStartLoadingNext) {
        loadMore()
        // console.log("loadMore() called")
    }
})