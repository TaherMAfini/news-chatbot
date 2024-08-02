const populateLatestTable = async () => {
    const response = await fetch('/news/get-all-records')
    const data = await response.json()
    let columns = data.columns
    let rows = data.rows

    let table = document.querySelector('#latest-table')
    table.classList.add('table')
    table.classList.add('table-responsive')
    let thead = table.appendChild(document.createElement('thead'))
    thead.classList.add('table-dark')
    thead.classList.add('text-center')
    thead.classList.add('sticky-top')
    let header = thead.appendChild(document.createElement('tr'))
    columns.forEach(column => {
        let th = header.appendChild(document.createElement('th'))
        th.classList.add('font-bold')
        th.textContent = column
        th.classList.add('text-lg')
    })
    let tbody = table.appendChild(document.createElement('tbody'))

    let primary = true
    rows.forEach(row => {
        let tr = tbody.appendChild(document.createElement('tr'))
        if (primary){
            tr.classList.add('table-primary')
            primary = false
        } else {
            tr.classList.add('table-secondary')
            primary = true
        }
        columns.forEach(column => {
            if(column === 'Transcript'){
                let td = tr.appendChild(document.createElement('td'))
                td.setAttribute('style', 'width: 50%; padding: 5px')
                let div = td.appendChild(document.createElement('div'))
                div.textContent = row[column]
                div.setAttribute('style', 'max-height: 200px; overflow-y: auto;')
            }else if (column === 'URL'){
                let td = tr.appendChild(document.createElement('td'))
                let a = td.appendChild(document.createElement('a'))
                a.textContent = 'Link'
                a.href = row[column]
                a.setAttribute('target', '_blank')
            } else if (column === 'Summary'){
                let td = tr.appendChild(document.createElement('td'))
                let a = td.appendChild(document.createElement('a'))
                a.textContent = 'Summary'
                a.href = '/summarize?id=' + row[column]

            } else {
                tr.appendChild(document.createElement('td')).textContent = row[column]
            }
        })
    })
}

if(window.location.pathname === '/latest'){
    populateLatestTable()
}

const populateSummaryTable = async (id) => {
    let h3 = document.querySelector('#video-title')
    h3.textContent = 'Loading...'
    const response = await fetch('/news/get-summary?id=' + id)
    const data = await response.json()

    if(data.message){
        let h3 = document.querySelector('#video-title')
        h3.textContent = data.message
        return
    }

    let title = data.title
    delete data.title
    let columns = Object.keys(data)
    let row = Object.values(data)

    h3.textContent = title

    let table = document.querySelector('#summary-table')
    table.classList.add('table')
    table.classList.add('table-responsive')
    let thead = table.appendChild(document.createElement('thead'))
    thead.classList.add('table-dark')
    thead.classList.add('text-center')
    thead.classList.add('sticky-top')
    let header = thead.appendChild(document.createElement('tr'))
    columns.forEach(column => {
        let th = header.appendChild(document.createElement('th'))
        th.classList.add('font-bold')
        th.textContent = column
        th.classList.add('text-lg')
    })
    let tbody = table.appendChild(document.createElement('tbody'))

    let tr = tbody.appendChild(document.createElement('tr'))
    
    let td = tr.appendChild(document.createElement('td'))
    td.setAttribute('style', 'width: 50%; padding: 5px')
    let div = td.appendChild(document.createElement('div'))
    div.textContent = row[0]
    div.setAttribute('style', 'max-height: 400px; overflow-y: auto;')

    let td2 = tr.appendChild(document.createElement('td'))
    td2.setAttribute('style', 'width: 50%; padding: 5px')
    let div2 = td2.appendChild(document.createElement('div'))
    div2.textContent = row[1]
    div2.setAttribute('style', 'max-height: 400px; overflow-y: auto;')

}

if(window.location.pathname === '/summarize'){
    const urlParams = new URLSearchParams(window.location.search)
    const id = urlParams.get('id')
    populateSummaryTable(id)
}

const getChatResponse = async (message) => {
    if(message === ''){
        return
    } 
    const chat = document.getElementById('chat-content')

    let userDiv = chat.appendChild(document.createElement('div'))
    userDiv.classList.add('user-message', 'mb-2', 'mt-4')
    userDiv.textContent = message
    userDiv.scrollIntoView({behavior: 'smooth'})

    let botDiv = chat.appendChild(document.createElement('div'))
    botDiv.classList.add('bot-response', 'mb-2')
    botDiv.textContent = 'Loading...'
    botDiv.scrollIntoView({behavior: 'smooth'})

    const url = '/news/search?query=' + encodeURIComponent(message)
    const data = await fetch(url)
    const response = await data.json()
    console.log(response)
    if(response.response === ''){
        botDiv.textContent = 'Sorry, I could not find any information on that topic'
        botDiv.scrollIntoView({behavior: 'smooth'})
        return
    }
    botDiv.textContent = response.response
    botDiv.scrollIntoView({behavior: 'smooth'})

}

if(window.location.pathname === '/chat') {
    const send = document.getElementById('chat-send')

    send.addEventListener('click', async () => {
        let chatbox = document.getElementById('chat-input')
        let message = chatbox.value.trim()
        chatbox.value = ''
        await getChatResponse(message)
        
    })
}