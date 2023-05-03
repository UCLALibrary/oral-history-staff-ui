function validateEditItemForm() {
    validMissing = checkMissingValues()
    validDuplicates = checkDuplicateValues()
    if (!(validMissing && validDuplicates)) {
        return false
    }
}

function checkMissingValues(){
    // all "optional" metadata other than Language and Format, which don't have types
    const valuesToCheck = ["alt_id","alt_title","copyright","date","description","name","publisher","resource","subject"]
    // more human-readable names, in the same order, for display
    const formattedNames = ["Alt ID","Alt Title","Copyright","Date","Description","Name","Publisher","Resource","Subject"]

    for (let i = 0; i < valuesToCheck.length; i++) {
        // find the type and value inputs for each data type, ignoring hidden or "__prefix__"
        typeQuery=`[name^=${valuesToCheck[i]}s][name$="type"]:not([name*="prefix"])`
        valueQuery=`[name^=${valuesToCheck[i]}s][name$="value"]:not([name*="prefix"])`
        types = document.querySelectorAll(typeQuery)
        values = document.querySelectorAll(valueQuery)

        // for each type, check existence of type and value
        // if exactly one exists, alert user of the problem and do not submit form
        for (let j = 0; j < types.length; j++) {
            if ((types[j].value && !values[j].value) || (values[j].value && !types[j].value)) {
                alert(`Please enter both a qualifier and a value for ${formattedNames[i]}.`)
                return false
            }
        }
    }
    return true
}

function checkDuplicateValues(){
    // only fields with limited values and Types
    const valuesToCheck = ["copyright","name","publisher","resource","subject"]
    // more human-readable names, in the same order, for display
    const formattedNames = ["Copyright","Name","Publisher","Resource","Subject"] 
    for (let i = 0; i < valuesToCheck.length; i++) {
        // find the type and value inputs for each data type, ignoring hidden or "__prefix__"
        typeQuery=`[name^=${valuesToCheck[i]}s][name$="type"]:not([name*="prefix"])`
        valueQuery=`[name^=${valuesToCheck[i]}s][name$="value"]:not([name*="prefix"])`
        typesNodes = Array.from(document.querySelectorAll(typeQuery))
        valuesNodes = Array.from(document.querySelectorAll(valueQuery))
        // get array of values from each for easier iterating
        types = []
        values = []
        for (let j = 0; j < typesNodes.length; j++) {
            types.push(typesNodes[j].value)
            values.push(valuesNodes[j].value)
        }
        // for each qualifier, check if it's repeated
        for (let j = 0; j < types.length; j++) {
            duplicateTypeIndices = []
            types.filter(function(element, index) {
                if(element == types[j]) {
                  duplicateTypeIndices.push(index)
                }
            })

            // if we have more than 1 of the same qualifier:
            // check if any values at the same indices are duplicates
            potentialDuplicateValues = []
            if (duplicateTypeIndices.length > 1){
                for (let k = 0; k < duplicateTypeIndices.length; k++){
                    potentialDuplicateValues.push(values[duplicateTypeIndices[k]]) 
                 }
                 valuesSet = new Set(potentialDuplicateValues)
                 if (valuesSet.size != potentialDuplicateValues.length){
                     alert(`Duplicate qualifier and value found for ${formattedNames[i]}.`)
                     return false
                 }
            }         
        }
    }
    // simplified check for language, which has no qualifier
    langValueQuery=`[name^="languages"][name$="value"]:not([name*="prefix"])`
    langNodes = document.querySelectorAll(langValueQuery)
    languages = []
    for (let i = 0; i < langNodes.length; i++) {
        languages.push(langNodes[i].value)
    }
    langSet = new Set(languages)
    if (langSet.size != languages.length){
        alert("Duplicate value found for Language.")
        return false
    }
    return true
}

function validateSearchForm() {
    if (document.getElementById("id_search_type").value == "status") {
        if (document.getElementById("id_status_query").value == "") {
            alert("Please select a Status value.")
            return false
        }
    }
    else {
        if (document.getElementById("id_char_query").value.trim().length === 0 ) {
            alert("Please enter a search query.")
            return false
        }
    }
}