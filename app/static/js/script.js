let fetchInterval;

function addOption(selectId, inputId) {
    var select = document.getElementById(selectId);
    var input = document.getElementById(inputId);
    var value = input.value.trim();

    if (value) {
        var option = document.createElement('option');
        option.textContent = value;
        option.value = value;
        option.className = 'list-item';

        select.appendChild(option);
        input.value = '';
    }
}

function removeOption(event) {
    if (event.target && event.target.classList.contains('list-item')) {
        var select = event.target.parentElement;
        select.removeChild(event.target);
    }
}

document.getElementById('list1').addEventListener('dblclick', removeOption);
document.getElementById('list2').addEventListener('dblclick', removeOption);

//checking that both list are not empty
function validateAndSearch() {
    var list1 = document.getElementById('list1');
    var list2 = document.getElementById('list2');

    if (list1.options.length === 0 || list2.options.length === 0) {
        alert("Both lists must have at least one item.");
        return;
    }

    search();
}

// Function sends start command to server and starts timer for sending request get_request
function search() {
    const searchButton = document.getElementById('searchButton');
    searchButton.disabled = true;
    const saveButton = document.getElementById('saveButton');
    saveButton.disabled = true;
    var list1 = Array.from(document.getElementById('list1').options).map(option => option.value);
    var list2 = Array.from(document.getElementById('list2').options).map(option => option.value);

    fetch('/start_search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            list1: list1,
            list2: list2
        })
    })
    .then(response => response.json())
    .then(data => {
        const messageContainer = document.getElementById('messageContainer');
        messageContainer.innerHTML = '';
        if (Array.isArray(data.messages)) {
            data.messages.forEach(message => {
                const p = document.createElement('p');
                p.textContent = message;
                messageContainer.appendChild(p);
            });
        }
        document.getElementById('resultContainer').textContent = '';
        //timer for getting messages about searching
        if (fetchInterval) {
            console.log('Clearing existing fetchInterval');
            clearInterval(fetchInterval);
            fetchInterval = null;
        }

        console.log('Setting fetchInterval for fetchMessages');
        fetchInterval = setInterval(fetchMessages, 2000);
    })
    .catch(error => {
        document.getElementById('messageContainer').textContent = 'An error occurred during search.';
    });
}


//function  gets messaget from server and updates message_container
function fetchMessages() {
    console.log('Calling fetchMessages...');
    fetch('/get_messages')
    .then(response => response.json())
    .then(data => {
        const messageContainer = document.getElementById('messageContainer');
        
        if (Array.isArray(data.messages)) {
            data.messages.forEach(message => {
                const p = document.createElement('p');
                p.textContent = message;
                messageContainer.appendChild(p);
            });
            messageContainer.scrollTop = messageContainer.scrollHeight;     
        }
        const resultContainer = document.getElementById('resultContainer');
        //check if responce has result block, timer should stop
        if (data.results) {
            resultContainer.innerHTML = '';
            //may be answer will be array
            if (Array.isArray(data.results)) {
                data.results.forEach(result => {
                    for (const [key, value] of Object.entries(result)) {
                        const p = document.createElement('p');
                        const a = document.createElement('a');
                        a.textContent = key;
                        a.href = key;
                        a.target = "_blank"
                        p.appendChild(a);
                        resultContainer.appendChild(p);
                    }
                });
            } 
            // if results are dictionary (object)
            else {
                for (const [key, value] of Object.entries(data.results)) {
                    const p = document.createElement('p');
                    const store_link = document.createElement('a');
                    store_link.textContent = key;
                    store_link.href = key;
                    store_link.target = "_blank"
                    p.appendChild(store_link);
                    for (const [innerKey, innerValue] of Object.entries(value)) {
                        if (innerValue.link) {  
                            const product_link = document.createElement('a');
                            product_link.textContent = innerValue.title;
                            product_link.href = innerValue.link;
                            product_link.target = "_blank";
                            product_link.style.margin = "10px 0px 10px 20px";
                            p.appendChild(document.createElement('br'));                          
                            p.appendChild(product_link);                         
                        }
                    }
                    p.style.marginBottom = '10px';                       
                    resultContainer.appendChild(p);
                }
            }
        
            resultContainer.scrollTop = resultContainer.scrollHeight;
        }
        // else {
        // console.warn('No results or results is not an array');
        // resultContainer.textContent = 'No results available.';
        // }
        if (data.search_finished) {
            clearInterval(fetchInterval);
            const searchButton = document.getElementById('searchButton');
            searchButton.disabled = false;
            const saveButton = document.getElementById('saveButton');
            saveButton.disabled = false;
        }

    })
    .catch(error => console.error('Error fetching messages:', error));
}


//function sends stop command to server for stop search
function stop_search() {

    fetch('/stop_search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            stop_search: true
        })
    })
    .then(response => {
        if (response.ok) {
            clearInterval(fetchInterval);
            console.log('Search stopped');
        } else {
            console.error('Failed to stop search');
        }
    })
    .catch(error => console.error('Error:', error))
    .finally(() => {
        const searchButton = document.getElementById('searchButton');
        searchButton.disabled = false;
    });
}

//function saves results, messages and search_lists into DB om server
function save_search(){
    var list1 = Array.from(document.getElementById('list1').options).map(option => option.value);
    var list2 = Array.from(document.getElementById('list2').options).map(option => option.value);
    var messages_html = document.getElementById('messageContainer').innerHTML;
    var results_html = document.getElementById('resultContainer').innerHTML;

    fetch('/save_search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            list1: list1,
            list2: list2,
            messages_html: messages_html,
            results_html: results_html 
        })
    })
    .then(response => {
        if (response.ok) {           
            console.log('Search saved');
        } else {
            console.error('Failed to stop search');
        }
    })
    .catch(error => console.error('Error:', error))
    .finally(() => {
        const searchButton = document.getElementById('searchButton');
        searchButton.disabled = false;
    });
}



