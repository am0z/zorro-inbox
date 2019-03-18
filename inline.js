(function(window) {
    const parent = window.parent
    const fixLinks = function() {
        let links = [].slice.call(document.getElementsByTagName('a'));
        links.forEach(function(link) {
            link.setAttribute('target', '_blank')
        })
    }
    const bindKeyPresses = function() {
        window.addEventListener('keydown', function(event) {
            let newEvent = document.createEvent("KeyboardEvent")
            newEvent.initKeyEvent(
                'keydown',
                event.bubbles,
                event.cancelable,
                parent,
                event.ctrlKey,
                event.altKey,
                event.shiftKey,
                event.metaKey,
                event.keyCode,
                event.charCode
            )
            parent.document.activeElement.blur()
            parent.document.dispatchEvent(newEvent)
        })
    }
    if (parent !== window) {
        bindKeyPresses()
    }
    window.onload = fixLinks
})(window)
