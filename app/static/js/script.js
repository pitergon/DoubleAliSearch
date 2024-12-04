let fetchInterval = null;
let pressTimer;
const LONG_PRESS_DURATION = 500;

document.addEventListener("DOMContentLoaded", function () {

  const resultsData = JSON.parse(document.getElementById("results-data").value || "{}");
  const messagesList = JSON.parse(document.getElementById("messages-list").value || "[]");
  loadMessages(messagesList);
  loadResults(resultsData);

  document.getElementById("add-to-list1").addEventListener("click", function () {
    addOption('namesList1', 'input1');
  });
  document.getElementById("add-to-list2").addEventListener("click", function () {
    addOption('namesList2', 'input2');
  });

  const list1 = document.getElementById("namesList1");
  const list2 = document.getElementById("namesList2");

  list1.addEventListener("dblclick", removeOption);
  list2.addEventListener("dblclick", removeOption);
  //for touchscreen devices
  list1.addEventListener("touchstart", handleLongPressStart);
  list2.addEventListener("touchstart", handleLongPressStart);
  list1.addEventListener("touchend", handleLongPressEnd);
  list2.addEventListener("touchend", handleLongPressEnd);

  document.getElementById("search-button").addEventListener("click", validateAndSearch);
  document.getElementById("stop-button").addEventListener("click", stopSearch);
  document.getElementById("save-button").addEventListener("click", saveSearch);


  if (isActiveSearch) {
    startPolling();
  }
});

//for touchscreen devices
function handleLongPressStart(event) {
  if (event.target && event.target.tagName === "OPTION") {
    pressTimer = setTimeout(() => {
      removeOption(event);
    }, LONG_PRESS_DURATION);
  }
}

//for touchscreen devices
function handleLongPressEnd(event) {
  clearTimeout(pressTimer);
}

//function adds option with product name to related select list
function addOption(selectId, inputId) {
  const select = document.getElementById(selectId);
  const input = document.getElementById(inputId);
  let value = input.value.trim();

  if (value) {
    const option = document.createElement("option");
    option.textContent = value;
    option.value = value;
    select.appendChild(option);
    input.value = "";
  }
}

//functions removes selected option with product name from related select list
function removeOption(event) {
  if (event.target && event.target.tagName === "OPTION") {
    let select = event.target.parentElement;
    select.removeChild(event.target);
  }
}

//checking that both list are not empty
function validateAndSearch() {
  const namesList1 = document.getElementById("namesList1");
  const namesList2 = document.getElementById("namesList2");

  if (namesList1.options.length === 0 || namesList2.options.length === 0) {
    alert("Both lists must have at least one item.");
    return;
  }
  startSearch();
}

//function sends start command to server
function startSearch() {
  const searchButton = document.getElementById("search-button");
  searchButton.disabled = true;
  const saveButton = document.getElementById("save-button");
  saveButton.disabled = true;
  const namesList1 = Array.from(document.getElementById("namesList1").options).map((option) => option.value);
  const namesList2 = Array.from(document.getElementById("namesList2").options).map((option) => option.value);

  fetch("/search/start", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      names_list1: namesList1,
      names_list2: namesList2,
    }),
  })
    .then(response => {
      if (response.redirected) {
        window.location.href = response.url;
        return;
      }
      return response.json();
    })
    .then((data) => {
      if (data) {
        if (data.error) {
          alert(data.messages);
          const searchButton = document.getElementById("search-button");
          searchButton.disabled = true;
        }

      }
    })
    .catch((error) => {
      console.error("Error during fetch:", error);
      document.getElementById("messages-container").textContent = "An error occurred during search.";
    });
}

//function starts polling for messages
function startPolling() {
  console.log("Polling started...");
  if (fetchInterval !== null) {
    console.log("Polling is already running.");
    return;
  }
  fetchInterval = setInterval(fetchMessages, 2000);
}

//function stops polling for messages
function stopPolling() {
  console.log("Polling stopped.");
  clearInterval(fetchInterval);
  fetchInterval = null;
}

//function  gets messages from server and updates message_container
function fetchMessages() {
  console.log("fetchMessages...");
  const url = window.location.href;
  const uuid = url.split('/').pop();
  fetch("/search/" + uuid + "/messages")
    .then((response) => response.json())
    .then((data) => {
      const messagesListField = document.getElementById("messages-list");
      let messagesList = JSON.parse(messagesListField.value || "[]");
      if (Array.isArray(data.messages)) {
        loadMessages(data.messages);  //load messages to messages-container
        messagesList = messagesList.concat(data.messages);
        messagesListField.value = JSON.stringify(messagesList); //save messages to hidden field
      }

      //check if response has result block, timer should stop
      if (data.results) {

        loadResults(data.results);  //load results to results-container
        const resultsListField = document.getElementById("results-data");
        resultsListField.value = JSON.stringify(data.results); //save results to hidden field
      }
      if (data.search_finished ) {
        clearInterval(fetchInterval);
        document.getElementById("search-button").disabled = false;
        document.getElementById("save-button").disabled = false;
      }
      if (data.error) {
        clearInterval(fetchInterval);
        document.getElementById("search-button").disabled = false;
        document.getElementById("save-button").disabled = false;
        alert(data.messages);
        console.error("Error fetching messages:", data.messages);
      }
    })
    .catch((error) => console.error("Error fetching messages:", error));
}

//function sends stop command to server for stop search
function stopSearch() {
  const url = window.location.href;
  const uuid = url.split('/').pop();
  fetch("/search/" + uuid + "/stop", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      stop_search: true,
    }),
  })
    .then((response) => {
      stopPolling()
      document.getElementById("search-button").disabled = false;
      return response.json();
    })
    .then((data) => {
      if (data) {
        if(data.error){
          console.error("Failed to stop search");
        }
        if (data.messages) {
          alert(data.messages);
          console.log(data.messages);
        }
      }
    })
    .catch((error) => console.error("Error:", error))
}

//function sends save command to server for save search
function saveSearch() {
  document.getElementById("save-button").disabled = true;
  let namesList1 = Array.from(document.getElementById("namesList1").options).map((option) => option.value);
  let namesList2 = Array.from(document.getElementById("namesList2").options).map((option) => option.value);
  const messagesList = JSON.parse(document.getElementById("messages-list").value || "[]");
  const resultsData = JSON.parse(document.getElementById("results-data").value || "{}");

  const url = window.location.href;
  const uuid = url.split('/').pop();

  fetch("/search/" + uuid + "/save", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      names_list1: namesList1,
      names_list2: namesList2,
      messages: messagesList,
      results: resultsData,
    }),
  })
    .then((response) => {
      return response.json();
    })
    .then((data) => {
      if (data) {
        if (data.error) {
          console.error("Failed to save search");
        } else {
          console.log("Search saved");
        }
        if (data.messages) {
          alert(data.messages);
          console.log(data.messages);
        }
      }
    })
    .catch((error) => console.error("Error:", error))
}

//function loads results from dictionary to results-container
function loadResults(resultData) {
  const resultsContainer = document.getElementById("results-container");
  resultsContainer.innerHTML = "";

  if (!resultData || Object.keys(resultData).length === 0) {
    const p = document.createElement("p");
    p.textContent = "No results found";
    resultsContainer.appendChild(p);
    return;
  }

  const ol = document.createElement("ol");
  ol.classList.add("list-decimal", "pl-6");
  const aClassNames = ["text-red-600", "hover:text-red-900", "hover:underline"];

  for (const [key, value] of Object.entries(resultData)) {
    //Create li tag with link to store for each store in resultData
    const liStore = document.createElement("li");
    const storeLink = document.createElement("a");
    storeLink.textContent = key;
    storeLink.href = key;
    storeLink.target = "_blank";
    storeLink.classList.add(...aClassNames);
    liStore.appendChild(storeLink);

    const ul = document.createElement("ul");
    ul.classList.add("list-disc", "pl-6");

    for (const innerValue of Object.values(value)) {
      if (!innerValue.link || !innerValue.currency || !innerValue.sale_price || !innerValue.title) {
        console.warn("Incomplete product data:", innerValue);
      }
      //Create li tag with product info and link for each product in store
      const liProduct = document.createElement("li");
      const productLink = document.createElement("a");
      productLink.textContent = `${innerValue.currency || ''} ${innerValue.sale_price || ''} ${innerValue.title || ''}`;
      productLink.href = innerValue.link;
      productLink.target = "_blank";
      productLink.classList.add(...aClassNames);
      liProduct.appendChild(productLink);
      ul.appendChild(liProduct);
    }

    liStore.appendChild(ul);
    ol.appendChild(liStore);
  }

  resultsContainer.appendChild(ol);
  resultsContainer.scrollTop = resultsContainer.scrollHeight;
}


//functions loads messages to messages-container from hidden field
function loadMessages(messagesList) {
  const messagesContainer = document.getElementById("messages-container");
  messagesList.forEach((message) => {
    const p = document.createElement("p");
    p.textContent = message;
    messagesContainer.appendChild(p);
  });
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}
