async function get_relevant_lessons(domen, token) {
    let url = `api/get-relevant-lessons`
    let headers = {
        "Content-Type": "application/json",
        "X-CSRFToken": token
    }
    let change_status = await fetch(domen+url, {
        method: "GET",
        headers: headers,
    })
    .then(check_status)
    .then(res => res.json())
    return change_status
}

async function get_amount_lessons(domen, token) {
    let lessons = await get_relevant_lessons(domen, token)
    let amount_lessons = {}
    for (let lesson in lessons) {
        let date = lessons[lesson].date
        if (!amount_lessons[date]) {
            amount_lessons[date] = 1
        } else {
            amount_lessons[date] += 1
        }
    }
    return amount_lessons
}

async function showHighCostNotification() {
    highCostNotification.style.animation = 'show-notice 1s forwards'
    highCostNotification.style.display = 'flex'
    highCostNotification.style.visibility = 'visible'
}

async function closeHightCostNotification() {
    highCostNotification.style.animation = 'close-notice 1s forwards'
    setTimeout(() => {highCostNotification.style.display = 'none'}, 500)
}


lessons = get_amount_lessons(domen, token)

lessonForm.addEventListener("submit", function(event) {
    lessons.then(
        res => {
            let amount = res[this.date.value]
            if (amount >= 4) {
                showHighCostNotification()
                event.preventDefault()
            }
        }
    )
})

highCostNotification.addEventListener('click', function(event) {
    if (event.target == event.currentTarget) {
        closeHightCostNotification()
    }
}, false);

window.addEventListener("keydown", function(event) {
    if (event.keyCode === 27) {
        closeHightCostNotification()
    }
}, false);

function toggleOrientationCostNotice() {

    if (window.orientation == undefined) {
        return
    }
    if (window.orientation == 0) {
        highCostMainImg.classList.add('increased')
        highCostCloseBtn.classList.add('increased')
        highCostContinueBtn.classList.add('increased')

        console.log(0)
    } else if ((window.orientation == 90) || (window.orientation == -90)) {
        highCostMainImg.classList.remove('increased')
        highCostCloseBtn.classList.remove('increased')
        highCostContinueBtn.classList.remove('increased')
        console.log(90)
    }
}

toggleOrientationCostNotice()
window.addEventListener("orientationchange", function() {
    toggleOrientationCostNotice()
}, false);
