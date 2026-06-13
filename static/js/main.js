function toggleTheme(){

    document.body.classList.toggle(
        "dark-mode"
    );

    localStorage.setItem(

        "theme",

        document.body.classList.contains(
            "dark-mode"
        )
    );
}

window.onload=function(){

    if(
        localStorage.getItem(
            "theme"
        )==="true"
    ){

        document.body.classList.add(
            "dark-mode"
        );
    }
}
