    /**
     * Getting user token
     * @param {String} domen
     * @param {String} id
     * @param {String} phone
     * @param {String} telegram
     * @param {String} token
     * @return {Promise<object>} user_token
    */
    async function get_token(domen, id, phone, telegram, token) {
        let url = 'api/get-token'
        let data = {
            'phone': phone,
            'telegram': telegram
        }
        let headers = {
            "Content-Type": "application/json",
            "X-CSRFToken": token
        }
        let user_token = await fetch(domen+url, {
            method: "POST",
            headers: headers,
            body: JSON.stringify(data),
        })
        .then(check_status)
        .then(res => res.json())
        return user_token
    }

    /**
     * Getting user information about notification
     * @param {String} domen
     * @param {String} id
     * @param {String} user_token
     * @return {Promise<object>} user_token
     * @example
     * // Returns {"notice": true, "amount_lesson": 2}
    */
    async function get_user_notice_info(domen, id, user_token) {
        let url = `api/notification/${id}/`
        let headers = {
            "Content-Type": "application/json",
            "X-CSRFToken": token,
            "Authorization": `Token ${user_token}`
        }
        let notice_info = await fetch(domen+url, {
            method: "GET",
            headers: headers,
        })
        .then(check_status)
        .then(res => res.json())
        return notice_info
    }

    /**
     * switch notification status by user (don't disturb)
     * @param {String} domen
     * @param {String} id
     * @param {String} user_token
     * @param {String} token
     * @param {Boolean} status
     * @return {Promise<String>} change_status
    */
    async function change_notice_status(domen, id, user_token, token, status=false) {
        let url = `api/notification/${id}/`
        let headers = {
            "Content-Type": "application/json",
            "X-CSRFToken": token,
            "Authorization": `Token ${user_token}`
        }
        let data = {
            'notice': status
        }
        let change_status = await fetch(domen+url, {
            method: "PATCH",
            headers: headers,
            body: JSON.stringify(data),
        })
        .then(check_status)
        .then(res => res.json())
        close_notification()
        return change_status
    }

    let check_status = function(response) {
        if (response.status !== 200) {
            return Promise.reject(new Error(response.statusText))
        }
        return Promise.resolve(response)
    }

    /**
     * display the html object
     * @param {String} id
     * @param {String} user_token
    */
    async function show_notification(id, user_token) {
        if (!document.cookie.includes('notice=0')) {
            notice_info = await get_user_notice_info(domen, id, user_token)
            if (notice_info['notice'] == true) {
                let notification_field = document.getElementById('notification')
                notification_field.style.display = 'flex'
                notification_field.style.visibility = 'visible'
            }
        }
    }

    /**
     * closing the html object
    */
    async function close_notification() {
        let notification_field = document.getElementById('notification')
        notification_field.style.animation = 'close-notice 1s forwards'
        setTimeout(() => {notification_field.style.display = 'none'}, 500)
        let now = new Date()
        let lifetime = 24*60*60 - (now.getHours()*60*60 + now.getMinutes()*60 + now.getSeconds())
        lifetime = 2
        document.cookie = `notice=0;path=/;max-age=${lifetime}`
    }

    