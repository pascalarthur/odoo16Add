const logistic_form_element = document.getElementById('route_demand_form');


function populateExchangeRate() {
    const nad_to_usd_exchange_rate = parseFloat(logistic_form_element.getAttribute('data-nad-to-usd-exchange-rate'));
    document.getElementById('exchange_rate_display').innerText = `${parseFloat(nad_to_usd_exchange_rate).toFixed(5)} [NAD/USD]`;
}


function update_usd_price(container) {
    const nad_to_usd_exchange_rate = parseFloat(logistic_form_element.getAttribute('data-nad-to-usd-exchange-rate'));

    var price_nad_element = container.querySelector('.priceNad');
    var price_usd_element = container.querySelector('.priceUsd');

    price_usd_element.value = (price_nad_element.value / nad_to_usd_exchange_rate).toFixed(4);
}


function getTruckDiv() {
    var truckDetail = document.createElement('div');

    truckDetail.classList.add('truck-detail');
    truckDetail.innerHTML = `
        <input required type="text" name="horse_number[]" placeholder="Horse Number"/>
        <input required type="text" name="truck_number[]" placeholder="Trailer Number"/>
        <input required type="text" name="container_number[]" placeholder="Container Number"/>
        <input required type="text" name="driver_name[]" placeholder="Driver Name"/>
        <input required type="text" name="telephone_number[]" placeholder="Telephone Number"/>
        <input required type="number" name="max_load_per_truck[]" placeholder="Max. Load [kg]"/><br/>
        <input class="priceNad" required type="number" placeholder="Price in NAD" onchange="update_usd_price(this.parentNode)"/>
        <span class="currency-label">NAD</span><br/>
        <input readonly type="number" name="price_in_usd[]" class="priceUsd" placeholder="Price in USD"/>
        <span class="currency-label">USD</span><br/>
        <button class="backload-button" type="button" onclick="toggle_backload(this)">Add Backload</button>
        <button class="remove-truck-detail-button" type="button" onclick="removeTruckDetail(this)">Remove Truck</button>
    `;
    return truckDetail;
}


function addTruckDetail() {
    var truck_details_container = document.createElement('div');
    truck_details_container.classList.add('truck-details-container');

    var truckDetail = getTruckDiv()
    var heading = document.createElement('h3');
    heading.innerText = 'One-Way';
    truck_details_container.appendChild(heading);
    truck_details_container.appendChild(truckDetail);

    // Backload information
    var backloadDetail = document.createElement('div');
    backloadDetail.classList.add('backload-detail');
    backloadDetail.innerHTML = `
        <h3>Backload</h3>
        <input class="priceNad" type="number" placeholder="Price in NAD"/>
        <span class="currency-label">NAD</span><br/>
        <input readonly type="number" name="backload_price[]" class="priceUsd" placeholder="Price in USD"/>
        <span class="currency-label">USD</span>
    `;

    backloadDetail.addEventListener('change', function() { update_usd_price(backloadDetail) });

    backloadDetail.style.display = 'none';
    truck_details_container.appendChild(backloadDetail);

    var container = document.getElementById('truck_details_section');
    container.appendChild(truck_details_container);
}


function toggle_backload(button_element) {
    var backload_detail = button_element.parentNode.parentNode.querySelector('.backload-detail');

    if (backload_detail.style.display == 'none') {
        backload_detail.style.display = '';
        button_element.innerText = 'Remove Backload';
    } else {
        backload_detail.style.display = 'none';
        backload_detail.querySelector('input').value = 'NA';
        button_element.innerText = 'Add Backload';
    }
};


function removeTruckDetail(element) {
    element.parentNode.parentNode.remove();
};


window.onload = function() {
    populateExchangeRate(); // Populate the exchange rate on load
};


function handleSubmit() {
    logistic_form_element.submit(); // Submit the form
};