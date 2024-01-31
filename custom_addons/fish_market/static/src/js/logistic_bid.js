const formElement = document.getElementById('transport_order_form');
const nad_to_usd_exchange_rate = parseFloat(formElement.getAttribute('data-nad-to-usd-exchange-rate'));
const transport_product_product_ids = JSON.parse(formElement.getAttribute('data-transport-product-product-ids'));

const product_prodcut_ids = {};
const backload_ids = [];
const item_ids = [];
var truck_counter = 0;

function populateExchangeRate() {
    document.getElementById('exchange_rate_display').innerText = `${parseFloat(nad_to_usd_exchange_rate).toFixed(5)} [NAD/USD]`;
}

function addTruckDetail() {
    var container = document.getElementById('truck_details_container');
    var truckDetail = getTruckDiv('One-Way', -1)
    var heading = document.createElement('h3');
    heading.innerText = 'One-Way';
    container.appendChild(heading);
    container.appendChild(truckDetail);
}

function add_backload(one_way_element) {
    var truckDetail = getTruckDiv('Backload', parseInt(one_way_element.parentNode.dataset.index));
    var backload_heading = document.createElement('h3');
    backload_heading.innerText = 'Backload';
    one_way_element.parentNode.appendChild(backload_heading);
    one_way_element.parentNode.appendChild(truckDetail);

    // Remove the 'Add Backload' button
    one_way_element.style.display = 'none';

    truckDetail.querySelector('.remove-truck-detail-button').addEventListener('click', function() {
        one_way_element.style.display = '';
        backload_heading.style.display = 'none';
    });
};

function getTruckDiv(product_product_type, one_way_index) {
    var truckDetail = document.createElement('div');

    truckDetail.setAttribute('data-index', truck_counter);
    product_prodcut_ids[truck_counter] = transport_product_product_ids[product_product_type];
    backload_ids.push(one_way_index);
    item_ids.push(truck_counter);
    truck_counter += 1;

    truckDetail.class = 'truck-detail';
    truckDetail.classList.add('truck-detail');
    truckDetail.innerHTML = `
        <input type="text" name="horse_number[]" placeholder="Horse Number"/>
        <input type="text" name="truck_number[]" placeholder="Trailer Number"/>
        <input type="text" name="container_number[]" placeholder="Container Number"/>
        <input type="text" name="driver_name[]" placeholder="Driver Name"/>
        <input type="text" name="telephone_number[]" placeholder="Telephone Number"/>
        <input type="number" name="max_load_per_truck[]" placeholder="Max. Load [kg]"/>
        <input type="number" name="price_per_truck[]" placeholder="Price in NAD" onchange="updateUsdPrice(this)"/>
        <span class="priceUsd" style="margin-left: 10px;">0 USD</span>
        <button class="remove-truck-detail-button" type="button" onclick="removeTruckDetail(this)">Remove</button>
    `;
    if (product_product_type != 'Backload') {
        truckDetail.innerHTML += `
            <button class="backload-button" type="button" onclick="add_backload(this)">Add Backload</button>
        `;
    }

    return truckDetail;
}

function updateUsdPrice(element) {
    var nadPrice = element.value; // Get the value from the passed element
    var usdPrice = nadPrice / nad_to_usd_exchange_rate; // Perform the conversion

    // Find the corresponding 'priceUsd' element
    var priceUsdElement = element.nextElementSibling;
    while (!priceUsdElement.classList.contains('priceUsd')) {
        priceUsdElement = priceUsdElement.nextElementSibling;
        if (priceUsdElement == null) {
            break;
        }
    }

    if (priceUsdElement) {
        priceUsdElement.innerText = usdPrice.toFixed(2) + ' USD'; // Update the display
    }
}

function removeTruckDetail(element) {
    var index = parseInt(element.parentNode.dataset.index);
    product_prodcut_ids[index] = null;
    backload_ids.splice(index, 1);
    item_ids.splice(index, 1);

    element.parentNode.remove();
};

// Call these functions to initialize the form
window.onload = function() {
    populateExchangeRate(); // Populate the exchange rate on load
};

function handleSubmit() {
    console.log('Submitting form...', backload_ids);
    const form = document.getElementById('transport_order_form');
    Object.entries(product_prodcut_ids).forEach(([key, value], index) => {
        if (value) {
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = 'product_prodcut_ids[]';
            hiddenInput.value = value;
            form.appendChild(hiddenInput);

            const hiddenInputBackload = document.createElement('input');
            hiddenInputBackload.type = 'hidden';
            hiddenInputBackload.name = 'backload_ids[]';
            hiddenInputBackload.value = backload_ids[index];
            form.appendChild(hiddenInputBackload);

            const hiddenInputIds = document.createElement('input');
            hiddenInputIds.type = 'hidden';
            hiddenInputIds.name = 'item_ids[]';
            hiddenInputIds.value = item_ids[index];
            form.appendChild(hiddenInputIds);
        }
    });

    form.submit(); // Submit the form
};