function validateForm(){
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
        for (let j=0; j<types.length; j++) {
            if ((types[j].value && !values[j].value) || (values[j].value && !types[j].value)){
                alert(`Please enter both a qualifier and value for ${formattedNames[i]}.`)
                return false
            }
        }
    }
}
