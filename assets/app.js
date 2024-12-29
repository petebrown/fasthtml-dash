function toggleRequestInfo(subject) {
    let subject_tag = "expand-" + subject;
    let subject_var = "expanded-" + subject.replace(/ /g, "_")
    let classList = document.getElementById(subject).classList;

    classList.toggle("show");
    if (classList.contains('show')) {
        document.getElementById(subject_tag).innerHTML = "-" // &downarrow; Hide"
        document.getElementById(subject_var).style.display = "block";
    } else {
        document.getElementById(subject_tag).innerHTML = "+" // &rightarrow; Show"
        document.getElementById(subject_var).style.display = "none";
    }
}