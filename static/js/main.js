let buttons = document.querySelectorAll("button.add_formset");
buttons.forEach(btn => btn.addEventListener("click", showEmptyForm));

function showEmptyForm(event) {
    // Prevent button default behavior of submitting form.
    event.preventDefault();
    
    // Get metadata type from button id (e.g., name_add -> name).
    metadataType = this.id.replace("_add", "");
    
    // Find current number of forms being used for this type.
    // This comes from the hidden "management form" for the given type.
    // E.g., id_names_TOTAL_FORMS
    totalId = `id_${metadataType}s-TOTAL_FORMS`;
    total = document.getElementById(totalId);

    // Find empty form for this type.
    // E.g., name -> name_empty_form
    emptyForm = document.getElementById(metadataType + "_empty_form");
    
    // Clone it to make a new form for display.
    newForm = emptyForm.cloneNode(deep=true);
    
    // Update numeric prefix values for new form, using original total.
    // E.g., for the new 2nd form (0-based):
    // names-__prefix__-usage_id -> names-1-usage_id
    newFormNumber = total.value;
    newForm.innerHTML = newForm.innerHTML.replace(/__prefix__/g, newFormNumber);
    
    // Remove id & class, copied from emptyForm
    newForm.removeAttribute("id");
    newForm.classList.remove("empty_form");
    
    // Display the new form immediately before the (hidden) empty form.
    emptyForm.parentNode.insertBefore(newForm, emptyForm);
    
    // Finally, increment total forms for this type.
    // E.g., if there are now 2 name forms, value will change from 1 -> 2.
    total.value = Number(total.value) + 1;
}

// Disable file upload submit button once clicked.
// The button is restored to normal once Django completes processing and re-renders the form.
function disable_upload_button(form) {
	btn = form.elements.upload_button;
	btn.textContent = "Please wait...";
	btn.disabled = true;
}