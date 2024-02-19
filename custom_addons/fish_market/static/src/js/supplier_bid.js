// Access the data attributes
const supplier_form_element = document.getElementById('supplier_order_form');
const product_offer_form_element = document.getElementById('product_offer_form');


function populateAddressDropdown() {
    const addresses = JSON.parse(supplier_form_element.getAttribute('data-addresses'));

    var dropdown = document.getElementById('delivery_address_dropdown');
    dropdown.innerHTML = `<option value="">Select an address...</option>`;
    addresses.forEach(function(address) {
        dropdown.innerHTML += `<option value="${address}">${address}</option>`;
    });
    dropdown.innerHTML += `<option value="other">Type in address...</option>`;

    dropdown.addEventListener('change', function() {
        var otherAddressSection = document.getElementById('other_address_section');
        if (dropdown.value === 'other') {
            otherAddressSection.style.display = 'block'; // Show the Other Address input
        } else {
            otherAddressSection.style.display = 'none'; // Hide the Other Address input
        }
    });
}

function addProductTemplate() {
    const product_temp_vars_dict = JSON.parse(supplier_form_element.getAttribute('data-product-temp-vars-dict'));
    var container = document.getElementById('product_templates_container');
    var productTemplateDetail = document.createElement('div');
    productTemplateDetail.classList.add('product-template-detail');

    var controlsContainer = document.createElement('div');
    controlsContainer.classList.add('controls-container');

    var selectHTML = `<select class="product-select" name="product_id[]">
                        <option value="">Select a product...</option>`;
    Object.entries(product_temp_vars_dict).forEach(function([product_id, product]) {
        selectHTML += `<option value="${product_id}">${product['name']}</option>`;
    });
    selectHTML += `</select>`;

    controlsContainer.innerHTML = selectHTML +
        `<button type="button" onclick="removeProductTemplate(this)">Remove Product</button>`;

    var variantsContainer = document.createElement('div');
    variantsContainer.classList.add('variants-container');

    productTemplateDetail.appendChild(controlsContainer);
    productTemplateDetail.appendChild(variantsContainer);
    container.appendChild(productTemplateDetail);

    // Add button to add variants
    var addVariantButton = document.createElement('button');
    addVariantButton.type = 'button';
    addVariantButton.textContent = 'Add Variant';
    addVariantButton.onclick = function() { addVariantCombination(controlsContainer.querySelector('.product-select')) };
    productTemplateDetail.appendChild(addVariantButton);
}

function addVariantCombination(productSelect) {
    const product_temp_vars_dict = JSON.parse(supplier_form_element.getAttribute('data-product-temp-vars-dict'));

    var templateId = productSelect.value;
    if (!templateId) return; // Exit if no product template is selected

    var productTemplateDetail = productSelect.closest('.product-template-detail');
    var variantsContainer = productTemplateDetail.querySelector('.variants-container');
    var template_id = productSelect.value;

    var variantCombination = document.createElement('div');
    variantCombination.classList.add('variant-combination');

    var attributeSelectHTML = `<select class="product-select" name="variant_id[]">
                                <option value="">Select a variant...</option>`;

    var product_template_dict = product_temp_vars_dict[template_id]

    for (const [ii, element] of product_template_dict['product_variants_ids'].entries()) {
        var value = product_template_dict['product_variants_ids'][ii];
        attributeSelectHTML += `<option value="${value}">${product_template_dict['product_variants_str'][ii]}</option>`;
    }
    attributeSelectHTML += `</select>`;
    variantCombination.innerHTML += attributeSelectHTML;

    variantCombination.innerHTML += `
        <input type="number" name="product_quantity[]" required placeholder="Quantity [kg]" style="margin-left: 10px;"/><br/>
        <input class="priceNad" required type="number" placeholder="Price in NAD" onchange="update_usd_price(this.parentNode)"/>
        <span class="currency-label">NAD/Box</span><br/>
        <input readonly type="number" name="price_in_usd[]" class="priceUsd input-no-border" placeholder="Price in USD"/>
        <span class="currency-label">USD/Box</span><br/>
        <button type="button" onclick="removeVariantCombination(this)" style="margin-left: 10px;">Remove Variant</button>
    `;

    variantsContainer.appendChild(variantCombination);
}

function removeVariantCombination(button) {
    button.parentNode.remove();
}

function removeProductTemplate(button) {
    var productTemplateDetail = button.closest('.product-template-detail');
    productTemplateDetail.remove(); // This removes the entire product template section
}


function add_start_end_location(table_element, obj) {
    var start_end_location_items = {
        'Start Address:': ['route_start_street', 'route_start_street2', 'route_start_city', 'route_start_zip', 'route_start_state_id', 'route_start_country_id'],
        'End Address:': ['route_end_street', 'route_end_street2', 'route_end_city', 'route_end_zip', 'route_end_state_id', 'route_end_country_id']
    };

    for (const [key, value] of Object.entries(start_end_location_items)) {
        var tr_element = document.createElement('tr');
        tr_element.innerHTML = `<td><label class="my-label">${key}</label></td>`;
        var td_element = document.createElement('td');
        for (const [ii, item] of value.entries()) {
            if (item in obj && obj[item] != false) {
                var input_element = document.createElement('t');
                input_element.name = item;
                input_element.innerHTML = obj[item];
                td_element.appendChild(input_element);
                td_element.appendChild(document.createElement('br'));
            }
        }
        tr_element.appendChild(td_element);
        table_element.appendChild(tr_element);
    }
}


// PRODUCT OFFER TEMPLATE

function synch_price_product_offer(element) {
    element.parentNode.querySelector('.priceUsd').value = element.value;
}

function update_price_per_ton(priceUsd_element) {
    var max_load = priceUsd_element.parentNode.querySelector('.max-load').value;
    var price_per_ton = (priceUsd_element.value / max_load) * 1000;
    priceUsd_element.parentNode.querySelector('.pricePerTon').innerHTML = price_per_ton;
}

function add_product_offers() {
    const product_pricelist_items = JSON.parse(product_offer_form_element.getAttribute('data-product-pricelist-items-list'));
    const product_offer_form_container = product_offer_form_element.querySelector('#product_offer_templates_container')
    for (const [ii, item] of product_pricelist_items.entries()) {
        var date_start = item['date_start'] ? item['date_start'] : 'Date unspecified';
        var date_end = item['date_end'] ? item['date_end'] : 'Date unspecified';

        var max_load = item['max_load'] ? item['max_load'] : 'Max Load unspecified';

        var pricelist_item_element = document.createElement('div');

        pricelist_item_element.innerHTML = `
            <input hidden type="number" name="product_pricelist_item_id[]"/>
            <input hidden type="number" name="price_in_usd[]" class="priceUsd"/>
            <input hidden type="number" class="max-load"/>
            <p style="margin-bottom: 5">${date_start} (Start Date) - ${date_end} (End Date): ${max_load} [kg] (Max. Load) </p>
            <input type="number" onchange='synch_price_product_offer(this); update_price_per_ton(this);' placeholder="Price [USD]"/>
            <input type="number" name="approx_loading_time[]" placeholder="Approx. Loading Time [hours]"/>
            <input type="number" name="approx_offloading_time[]" placeholder="Approx. Offloading Time [hours]"/>
            <div style="margin-bottom: 5">Price per ton: <span class="pricePerTon">0.0</span> [USD/Ton]</div>
        `;
        pricelist_item_element.querySelector('input[name="product_pricelist_item_id[]"]').value = item['id'];
        pricelist_item_element.querySelector('input[name="price_in_usd[]"]').value = NaN;
        pricelist_item_element.querySelector('.max-load').value = max_load;

        product_offer_form_container.appendChild(pricelist_item_element);
    }
}

// Call these functions to initialize the form
window.onload = function() {
    populateExchangeRate(); // Populate the exchange rate on load
    if (supplier_form_element) {
        populateAddressDropdown(); // Populate the address dropdown on load
        addProductTemplate(); // Add at least one product template dropdown on load
    }

    if (logistic_form_element) {
        var start_end_route_details_element = logistic_form_element.querySelector('#table_info');
        add_start_end_location(start_end_route_details_element, JSON.parse(logistic_form_element.getAttribute('data-obj-start-end')));
    }

    if (product_offer_form_element) {
        var start_end_route_details_element = product_offer_form_element.querySelector('#table_info');
        add_start_end_location(start_end_route_details_element, JSON.parse(product_offer_form_element.getAttribute('data-obj-start-end')));
        add_product_offers(); // Populate the exchange rate on load
    }
};