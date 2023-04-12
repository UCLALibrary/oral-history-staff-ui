let buttons = document.querySelectorAll("button.add_formset");
buttons.forEach(btn => btn.addEventListener("click", showEmptyForm));

function showEmptyForm(event) {
    // Prevent button default behavior of submitting form.
    event.preventDefault();
    // Get metadata type from button id.
    metadataType = this.id.replace("_add", "");
    // Find current number of forms being used for this type.
    totalId = `id_${metadataType}s-TOTAL_FORMS`;
    total = document.getElementById(totalId);

    // Find empty form for this type.
    emptyForm = document.getElementById(metadataType + "_empty_form");
    // Clone it to make a new form for display.
    newForm = emptyForm.cloneNode(deep=true);
    // Update numeric prefix values for new form, using original total.
    // E.g., if total is 1 (1 existing form), the new form is the 2nd form,
    // so it will use (0-based) number 1.
    newFormNumber = total.value;
    newForm.innerHTML = newForm.innerHTML.replace(/__prefix__/g, newFormNumber);
    // Remove id & class, copied from emptyForm
    newForm.removeAttribute("id");
    newForm.classList.remove("empty_form");
    // Display the new form immediately before the (hidden) empty form.
    emptyForm.parentNode.insertBefore(newForm, emptyForm);
    // Finally, increment total forms for this type.
    total.value = Number(total.value) + 1;
}