function chooseMode(mode) {

  console.log("Selected mode:", mode);

  // go to flag screen
  window.location.href =
    `flags.html?mode=${encodeURIComponent(mode)}`;
}