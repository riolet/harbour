function appendElement(element){
    var proto = document.getElementById(element);
    var clone = proto.cloneNode(true);
    inputs = clone.getElementsByTagName("input");
    for (i=0;i<inputs.length;i++) {
        inputs[i].value = ""
    }
    proto.parentNode.appendChild(clone);
    console.log(proto, clone, allInputs);
}

function notifyLoading(element){
    var loading = document.getElementById ( "loading" ) ;
    loading.style.visibility = "visible" ;
}

function duplicateElement(element,parent){
    var proto = document.getElementById(element);
    var clone = proto.cloneNode(true);
    var parentElem = document.getElementById(parent);
    parentElem.appendChild(clone);
}