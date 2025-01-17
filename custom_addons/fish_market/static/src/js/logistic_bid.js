const logistic_form_element = document.getElementById('route_demand_form');
const form_content_element = document.getElementById('form_content');


function populateExchangeRate() {
    const nad_to_usd_exchange_rate = parseFloat(form_content_element.getAttribute('data-nad-to-usd-exchange-rate'));
    document.getElementById('exchange_rate_display').innerText = `${parseFloat(nad_to_usd_exchange_rate).toFixed(5)} [NAD/USD]`;
}


function update_usd_price(container) {
    const nad_to_usd_exchange_rate = parseFloat(form_content_element.getAttribute('data-nad-to-usd-exchange-rate'));

    var price_nad_element = container.querySelector('.priceNad');
    var price_usd_element = container.querySelector('.priceUsd');

    price_usd_element.value = (price_nad_element.value / nad_to_usd_exchange_rate).toFixed(4);
}


function update_max_load(element) {
    element.parentNode.querySelector('input[name="max_load_per_truck[]"]').value = 49_900 - element.value;
}


function getTruckDiv() {
    var truckDetail = document.createElement('div');

    truckDetail.classList.add('truck-detail');
    truckDetail.innerHTML = `
        <input hidden type="number" name="max_load_per_truck[]" placeholder="Max. Load [kg]"/><br/>
        <input required type="text" name="horse_number[]" placeholder="Horse Number"/>
        <input required type="text" name="trailer_number[]" placeholder="Trailer Number"/>
        <input required type="text" name="container_number[]" placeholder="Container Number"/>
        <input required type="text" name="driver_name[]" placeholder="Driver Name"/>
        <input required type="text" name="telephone_number[]" placeholder="Telephone Number"/>
        <input required type="number" onchange="update_max_load(this)" placeholder="GVM Truck & Trailer [kg]"/><br/>
        <input class="priceNad" required type="number" placeholder="Price in NAD" onchange="update_usd_price(this.parentNode)"/>
        <span class="currency-label">NAD</span><br/>
        <input readonly type="number" name="price_in_usd[]" class="priceUsd input-no-border" placeholder="Price in USD"/>
        <span class="currency-label">USD</span><br/>
        <table>
            <tr>
                <td><label>Estimated loading date and time:</label></td>
            </tr>
            <tr>
                <td><input required type="datetime-local" name="date_start[]"/></td>
            </tr>
            <tr>
                <td><label>Estimated arrival date and time at destination Address:</label></td>
            </tr>
            <tr>
                <td><input required type="datetime-local" name="date_end[]"/></td>
            </tr>
        </table>
        <button class="backload-button" type="button" onclick="toggle_backload(this)">Add Backload</button>
        <button class="remove-truck-detail-button" type="button" onclick="removeTruckDetail(this)">Remove Truck</button>
    `;
    return truckDetail;
}


function addTruck() {
    var truck_routes_container = document.createElement('div');
    truck_routes_container.classList.add('truck-details-container');

    var truckDetail = getTruckDiv()
    var heading = document.createElement('h3');
    heading.innerText = 'One-Way';
    heading.classList.add('bid-h3')
    truck_routes_container.appendChild(heading);
    truck_routes_container.appendChild(truckDetail);

    // Backload information
    var backloadDetail = document.createElement('div');
    backloadDetail.classList.add('backload-detail');
    backloadDetail.innerHTML = `
        <h3 class="bid-h3">Backload</h3>
        <input class="priceNad" type="number" placeholder="Price in NAD"/>
        <span class="currency-label">NAD</span><br/>
        <input readonly type="number" name="backload_price[]" class="priceUsd input-no-border" placeholder="Price in USD"/>
        <span class="currency-label">USD</span>
        <table>
            <tr>
                <td><label>Estimated arrival date and time at start Address:</label></td>
            </tr>
            <tr>
                <td><input type="datetime-local" name="date_end_backload[]"/></td>
            </tr>
        </table>
    `;
    backloadDetail.addEventListener('change', function() { update_usd_price(backloadDetail) });

    backloadDetail.style.display = 'none';
    truck_routes_container.appendChild(backloadDetail);

    var container = document.getElementById('truck_routes_section');
    container.appendChild(truck_routes_container);
}


function toggle_backload(button_element) {
    var backload_detail = button_element.parentNode.parentNode.querySelector('.backload-detail');

    if (backload_detail.style.display == 'none') {
        backload_detail.style.display = '';
        button_element.innerText = 'Remove Backload';
        backload_detail.querySelector('.priceNad').setAttribute('required', 'required');
        backload_detail.querySelector('input[name="date_end_backload[]"]').setAttribute('required', 'required');
    } else {
        backload_detail.style.display = 'none';
        backload_detail.querySelector('.priceNad').value = NaN;
        backload_detail.querySelector('.priceUsd').value = NaN;
        backload_detail.querySelector('.priceNad').removeAttribute('required');
        backload_detail.querySelector('input[name="date_end_backload[]"]').removeAttribute('required');
        button_element.innerText = 'Add Backload';
    }
};


function removeTruckDetail(element) {
    element.parentNode.parentNode.remove();
};
