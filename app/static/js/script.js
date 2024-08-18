document.addEventListener("DOMContentLoaded", function () {
  // loadMesseges();
  const resultsData = JSON.parse(document.getElementById("results-data").value || "{}");
  const messagesList = JSON.parse(document.getElementById("messages-list").value || "[]");
  loadMessages(messagesList);
  loadResults(resultsData);
});

let fetchInterval;

function addOption(selectId, inputId) {
  var select = document.getElementById(selectId);
  var input = document.getElementById(inputId);
  var value = input.value.trim();

  if (value) {
    var option = document.createElement("option");
    option.textContent = value;
    option.value = value;

    select.appendChild(option);
    input.value = "";
  }
}

function removeOption(event) {
  if (event.target && event.target.tagName === "OPTION") {
    var select = event.target.parentElement;
    select.removeChild(event.target);
  }
}

document.getElementById("list1").addEventListener("dblclick", removeOption);
document.getElementById("list2").addEventListener("dblclick", removeOption);

//checking that both list are not empty
function validateAndSearch() {
  var list1 = document.getElementById("list1");
  var list2 = document.getElementById("list2");

  if (list1.options.length === 0 || list2.options.length === 0) {
    alert("Both lists must have at least one item.");
    return;
  }

  search();
}

// Function sends start command to server and starts timer for sending request get_request
function search() {
  const searchButton = document.getElementById("search-button");
  searchButton.disabled = true;
  const saveButton = document.getElementById("save-button");
  saveButton.disabled = true;
  var list1 = Array.from(document.getElementById("list1").options).map((option) => option.value);
  var list2 = Array.from(document.getElementById("list2").options).map((option) => option.value);

  fetch("/start_search", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      list1: list1,
      list2: list2,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      const messageContainer = document.getElementById("messages-container");
      messageContainer.innerHTML = "";
      const messagesListField = document.getElementById("messages-list");
      messagesListField.value = "";
      const resultsListField = document.getElementById("results-data");
      resultsListField.value = "";
      if (Array.isArray(data.messages)) {
        loadMessages(data.messages);
      }
      document.getElementById("results-container").textContent = "";
      //timer for getting messages about searching
      if (fetchInterval) {
        console.log("Clearing existing fetchInterval");
        clearInterval(fetchInterval);
        fetchInterval = null;
      }

      console.log("Setting fetchInterval for fetchMessages");
      fetchInterval = setInterval(fetchMessages, 2000);
    })
    .catch((error) => {
      document.getElementById("messages-container").textContent = "An error occurred during search.";
    });
}

//function  gets messaget from server and updates message_container
function fetchMessages() {
  console.log("Calling fetchMessages...");
  fetch("/get_messages")
    .then((response) => response.json())
    .then((data) => {
      const messagesListField = document.getElementById("messages-list");
      let messagesList = JSON.parse(messagesListField.value || "[]");
      if (Array.isArray(data.messages)) {
        loadMessages(data.messages);
        messagesList = messagesList.concat(data.messages);
        messagesListField.value = JSON.stringify(messagesList);
      }

      //check if responce has result block, timer should stop
      if (data.results) {
        loadResults(data.results);
        const resultsListField = document.getElementById("results-data");
        resultsListField.value = JSON.stringify(data.results);
      }

      if (data.search_finished) {
        clearInterval(fetchInterval);
        const searchButton = document.getElementById("search-button");
        searchButton.disabled = false;
        const saveButton = document.getElementById("save-button");
        saveButton.disabled = false;
      }
    })
    .catch((error) => console.error("Error fetching messages:", error));
}

//function sends stop command to server for stop search
function stop_search() {
  fetch("/stop_search", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      stop_search: true,
    }),
  })
    .then((response) => {
      if (response.ok) {
        clearInterval(fetchInterval);
        console.log("Search stopped");
      } else {
        console.error("Failed to stop search");
      }
    })
    .catch((error) => console.error("Error:", error))
    .finally(() => {
      const searchButton = document.getElementById("search-button");
      searchButton.disabled = false;
    });
}

//function saves results, messages and search_lists into DB om server
function save_search() {
  let list1 = Array.from(document.getElementById("list1").options).map((option) => option.value);
  let list2 = Array.from(document.getElementById("list2").options).map((option) => option.value);
  const messagesList = JSON.parse(document.getElementById("messages-list").value || "[]");
  const resultsData = JSON.parse(document.getElementById("results-data").value || "{}");

  fetch("/save_search", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      list1: list1,
      list2: list2,
      messages: messagesList,
      results: resultsData,
    }),
  })
    .then((response) => {
      if (response.ok) {
        console.log("Search saved");
      } else {
        console.error("Failed to stop search");
      }
    })
    .catch((error) => console.error("Error:", error))
    .finally(() => {
      const searchButton = document.getElementById("search-button");
      searchButton.disabled = false;
    });
}

function loadResults(resultData) {
  const resultsContainer = document.getElementById("results-container");
  resultsContainer.innerHTML = "";
  if (Object.keys(resultData).length === 0) {
    const p = document.createElement("p");
    p.textContent = "No results found";  
    resultsContainer.appendChild(p);
  } else {
    const ol = document.createElement("ol");
    ol.classList.add("list-decimal", "pl-6");
    const aClassNames = ["text-red-600", "hover:text-red-900", "hover:underline"];
    for (const [key, value] of Object.entries(resultData)) {
      const liStore = document.createElement("li");
      const storeLink = document.createElement("a");
      storeLink.textContent = key;
      storeLink.href = key;
      storeLink.target = "_blank";
      storeLink.classList.add(...aClassNames);
      liStore.appendChild(storeLink);
      const ul = document.createElement("ul");
      ul.classList.add("list-disc", "pl-6");
      for (const [innerKey, innerValue] of Object.entries(value)) {
        if (innerValue.link) {
          const liProduct = document.createElement("li");
          const productLink = document.createElement("a");
          productLink.textContent = innerValue.currency + innerValue.sale_price + " " + innerValue.title;
          productLink.href = innerValue.link;
          productLink.target = "_blank";
          productLink.classList.add(...aClassNames);
          liProduct.appendChild(productLink);
          ul.appendChild(liProduct);
        }
      }
      liStore.appendChild(ul);
      ol.appendChild(liStore);
    }
    resultsContainer.appendChild(ol);
    resultsContainer.scrollTop = resultsContainer.scrollHeight;
  }
}

function loadMessages(messagesList) {
  const messagesContainer = document.getElementById("messages-container");
  messagesList.forEach((message) => {
    const p = document.createElement("p");
    p.textContent = message;
    messagesContainer.appendChild(p);
  });
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}
