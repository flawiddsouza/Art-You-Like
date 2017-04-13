document.addEventListener('DOMContentLoaded', function() {

    // modal handling code //

    var addNewArtBtn = document.getElementById('add-new-art')
    var addNewArtModal = document.getElementById('add-new-art-modal')
    var editArtModal = document.getElementById('edit-art-modal')

    if(addNewArtBtn) // only if add new art button exists on the given page
        addNewArtBtn.addEventListener('click', () => { addNewArtModal.classList.add('is-active') })
    addNewArtModal.getElementsByClassName('modal-close')[0].addEventListener('click', hideModal1)
    addNewArtModal.getElementsByClassName('modal-background')[0].addEventListener('click', hideModal1)

    editArtModal.getElementsByClassName('modal-close')[0].addEventListener('click', hideModal2)
    editArtModal.getElementsByClassName('modal-background')[0].addEventListener('click', hideModal2)

    function hideModal1() {
        addNewArtModal.classList.remove('is-active')
    }

    function hideModal2() {
        editArtModal.classList.remove('is-active')
    }

    window.addEventListener('keydown', e => { // hide modal when esc key is pressed
        if (e.key == "Escape") {
            hideModal1()
            hideModal2()
        }
    })

    // modal handling code //

    function inputEnabler(rootElement) { // enables all inputs under the given element
        var inputs = rootElement.getElementsByTagName('input')
        for(var input of inputs) {
            input.disabled = false
        }
        var dropdown = rootElement.getElementsByTagName('select')[0]
        if(typeof dropdown != "undefined") {
            dropdown.disabled = false
        }
    }

    function inputDisabler(rootElement) { // disables all inputs under the given element
        var inputs = rootElement.getElementsByTagName('input')
        for(var input of inputs) {
            input.disabled = true
        }
        var dropdown = rootElement.getElementsByTagName('select')[0]
        if(typeof dropdown != "undefined") {
            dropdown.disabled = true
        }
    }

    function activeToggle(activeElement, inactiveElements) { // (element to activate, elements to disable)
        activeElement.classList.remove('inactive')
        activeElement.classList.add('active')
        Array.from(inactiveElements).forEach((inactiveElement) => {
            inactiveElement.classList.remove('active')
        })
        Array.from(inactiveElements).forEach((inactiveElement) => {
            inactiveElement.classList.add('inactive')
        })
        inputEnabler(activeElement)
        Array.from(inactiveElements).forEach((inactiveElement) => {
            inputDisabler(inactiveElement)
        })
    }

    function activeToggleClickEvent(activeElement, inactiveElements) {
        if(activeElement) {
            activeElement.addEventListener('click', () => {
                activeToggle(activeElement, inactiveElements)
            })
        }
    }

    var imageOption1 = document.getElementById('image-option-1')
    var imageOption2 = document.getElementById('image-option-2')
    var artistOption1 = document.getElementById('artist-option-1')
    var artistOption2 = document.getElementById('artist-option-2')

    activeToggleClickEvent(imageOption1, [imageOption2])
    activeToggleClickEvent(imageOption2, [imageOption1])
    activeToggleClickEvent(artistOption1, [artistOption2])
    activeToggleClickEvent(artistOption2, [artistOption1])

    var imageOption0Edit = document.getElementById('image-option-0-edit')
    var imageOption1Edit = document.getElementById('image-option-1-edit')
    var imageOption2Edit = document.getElementById('image-option-2-edit')
    var artistOption1Edit = document.getElementById('artist-option-1-edit')
    var artistOption2Edit = document.getElementById('artist-option-2-edit')

    activeToggleClickEvent(imageOption0Edit, [imageOption1Edit, imageOption2Edit])
    activeToggleClickEvent(imageOption1Edit, [imageOption0Edit, imageOption2Edit])
    activeToggleClickEvent(imageOption2Edit, [imageOption0Edit, imageOption1Edit])
    activeToggleClickEvent(artistOption1Edit, [artistOption2Edit])
    activeToggleClickEvent(artistOption2Edit, [artistOption1Edit])

    let artGallery = document.getElementById('art-gallery')
    if(artGallery) { // if this element exists
        initEditDeleteButtons(artGallery)
    } else { // if it doesn't
        initEditDeleteButtons(document.getElementsByClassName('art-item')[0])
    }

    function initEditDeleteButtons(rootElement) {
        if(rootElement) {
            rootElement.addEventListener('click', e => {
                // confirm deletion
                if(e.target && e.target.matches('.item-delete') || e.target && e.target.matches('.item-delete > img')) {
                    e.preventDefault()
                    alertify.parent(document.body) // do this or include alertify at the end of body
                    alertify.confirm('Are you sure?', () => {
                        e.target.closest('form').submit()
                    })
                }
                // handle edit modal btn clicks
                if(e.target && e.target.matches('.edit-art') || e.target && e.target.matches('.edit-art > img')) {
                    var clickedButton = e.target.closest('.edit-art')
                    var tempObject = {}
                    tempObject.id = clickedButton.dataset.id
                    tempObject.title = clickedButton.dataset.title
                    tempObject.image_url = clickedButton.dataset.imageUrl
                    tempObject.artist_id = clickedButton.dataset.artistId
                    tempObject.source = clickedButton.dataset.source
                    vueInstance.selected_tags = eval(clickedButton.dataset.tags)
                    vueInstance.edit_modal_data = tempObject
                    editArtModal.classList.add('is-active')
                }
            })
        }
    }

    // give ability to close notifications
    let notifications = document.getElementsByClassName('notification')
    if(notifications) {
        Array.from(notifications).forEach((notification) => {
            notification.addEventListener('click', e => {
                if(e.target && e.target.matches('button.delete')) {
                    e.target.parentNode.remove()
                }
            })
        })
    }

    // hide alertify dialog when esc key is pressed
    document.addEventListener('click', e => {
        if(e.target && e.target.matches('.alertify')) {
            e.target.remove()
        }
    })

    // close alertify dialog if esc is pressed
    window.addEventListener('keyup', e => {
        if(e.which == 27) {
            if(typeof document.getElementsByClassName('alertify')[0] != "undefined") {
                document.getElementsByClassName('alertify')[0].remove()
            }
        }
    })
})

var vueInstance = new Vue({
    el: '#modals',

    data: {
        artists: [],
        tags: [],
        edit_modal_data: {},
        selected_tags: []
    },

    mounted() {
        fetch('/artist/all').then((response) => {
            return response.json()
        }).then((artists) => {
            this.artists = artists
        })
        fetch('/tag/all').then((response) => {
            return response.json()
        }).then((tags) => {
            this.tags = tags
        })
    }
})