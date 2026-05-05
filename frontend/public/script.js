// Animated multilingual Hello text
const greetings = [
  { text: "Hello", lang: "en" },
  { text: "مرحبا", lang: "ar" },
  { text: "Bonjour", lang: "fr" },
  { text: "Hallo", lang: "de" },
  { text: "Hola", lang: "es" },
  { text: "Привет", lang: "ru" },
  { text: "Merhaba", lang: "tr" },
  { text: "नमस्ते", lang: "hi" },
  { text: "হ্যালো", lang: "bn" },
  { text: "ሰላም", lang: "am" },
  { text: "ہیلو", lang: "ur" },
  { text: "سلام", lang: "ps" },
  { text: "ഹലോ", lang: "ml" },
  { text: "வணக்கம்", lang: "ta" },
  { text: "नमस्ते", lang: "ne" },
  { text: "Kamusta", lang: "tl" },
  { text: "你好", lang: "zh" },
  { text: "Halo", lang: "id" },
  { text: "Sawubona", lang: "zu" }
];

let greetingIndex = 0;

function updateGreeting() {
  const helloText = document.getElementById("helloText");
  const current = greetings[greetingIndex];

  helloText.innerText = current.text;

  // Font switching
  if (["ar", "ur", "ps"].includes(current.lang)) {
    helloText.style.fontFamily = "'Cairo', sans-serif";
    helloText.dir = "rtl";
  } else if (["hi", "ne"].includes(current.lang)) {
    helloText.style.fontFamily = "'Noto Sans Devanagari', sans-serif";
    helloText.dir = "ltr";
  } else if (current.lang === "bn") {
    helloText.style.fontFamily = "'Noto Sans Bengali', sans-serif";
    helloText.dir = "ltr";
  } else if (current.lang === "ml") {
    helloText.style.fontFamily = "'Noto Sans Malayalam', sans-serif";
    helloText.dir = "ltr";
  } else if (current.lang === "ta") {
    helloText.style.fontFamily = "'Noto Sans Tamil', sans-serif";
    helloText.dir = "ltr";
  } else if (current.lang === "zh") {
    helloText.style.fontFamily = "'Noto Sans SC', sans-serif";
    helloText.dir = "ltr";
  } else {
    helloText.style.fontFamily = "'Playfair Display', serif";
    helloText.dir = "ltr";
  }

  greetingIndex = (greetingIndex + 1) % greetings.length;
}

updateGreeting();
setInterval(updateGreeting, 2000);


// Flags + languages
const flags = [
  { country: "UAE", img: "assets/flags/uae-flag.png", languages: ["Arabic"] },
  { country: "USA", img: "assets/flags/usa-flag.png", languages: ["English"] },
  { country: "India", img: "assets/flags/india-flag.png", languages: ["Hindi", "Malayalam", "Tamil"] },
  { country: "Pakistan", img: "assets/flags/pakistan-flag.png", languages: ["Urdu", "Pashto"] },
  { country: "Bangladesh", img: "assets/flags/bangladesh-flag.png", languages: ["Bengali"] },
  { country: "Sri Lanka", img: "assets/flags/srilanka-flag.png", languages: ["Sinhala"] },
  { country: "Nepal", img: "assets/flags/nepal-flag.png", languages: ["Nepali"] },
  { country: "China", img: "assets/flags/china-flag.png", languages: ["Chinese"] },
  { country: "Ethiopia", img: "assets/flags/ethiopia-flag.png", languages: ["Amharic"] },
  { country: "South Africa", img: "assets/flags/south-africa-flag.png", languages: ["Afrikaans", "Zulu"] },
  { country: "Kenya", img: "assets/flags/kenya-flag.png", languages: ["Swahili"] },
  { country: "Somalia", img: "assets/flags/somalia-flag.png", languages: ["Somali"] },
  { country: "Indonesia", img: "assets/flags/indonesia-flag.png", languages: ["Indonesian"] },
  { country: "Philippines", img: "assets/flags/philippines-flag.png", languages: ["Tagalog"] },
  { country: "South Korea", img: "assets/flags/skorea-flag.png", languages: ["Korean"] },
  { country: "Japan", img: "assets/flags/japan-flag.png", languages: ["Japanese"] },
  { country: "Thailand", img: "assets/flags/thailand-flag.png", languages: ["Thai"] },
  { country: "Turkey", img: "assets/flags/turkey-flag.png", languages: ["Turkish"] },
  { country: "Uzbekistan", img: "assets/flags/uzbekistan-flag.png", languages: ["Uzbek"] },
  { country: "Russia", img: "assets/flags/russia-flag.png", languages: ["Russian"] },
  { country: "Spain", img: "assets/flags/spain-flag.png", languages: ["Spanish"] },
  { country: "France", img: "assets/flags/france-flag.png", languages: ["French"] },
  { country: "Portugal", img: "assets/flags/portugal-flag.png", languages: ["Portuguese"] },
  { country: "Germany", img: "assets/flags/germany-flag.png", languages: ["German"] }
];

const grid = document.getElementById("flagsGrid");
let activeDropdown = null;


// Render flags
flags.forEach(flag => {
  const card = document.createElement("div");
  card.className = "flag-card";

  const img = document.createElement("img");
  img.src = flag.img;
  img.alt = flag.country;

  card.appendChild(img);

  if (flag.languages.length > 1) {
    card.addEventListener("click", (e) => {
      e.stopPropagation();
      setActiveFlag(card);
      toggleDropdown(card, flag.languages);
    });
  } else {
    card.addEventListener("click", (e) => {
      e.stopPropagation();
      setActiveFlag(card);
      closeActiveDropdown();
      goNext(flag.languages[0]);
    });
  }

  grid.appendChild(card);
});


// Highlight selected flag
function setActiveFlag(card) {
  document.querySelectorAll(".flag-card").forEach(item => {
    item.classList.remove("active");
  });

  card.classList.add("active");
}


// Open / close dropdown
function toggleDropdown(parent, languages) {
  if (activeDropdown && activeDropdown !== parent) {
    closeActiveDropdown();
  }

  const existingDropdown = parent.querySelector(".dropdown");

  if (existingDropdown) {
    existingDropdown.remove();
    activeDropdown = null;
    parent.classList.remove("active");
    return;
  }

  const dropdown = document.createElement("div");
  dropdown.className = "dropdown";

  languages.forEach(language => {
    const button = document.createElement("button");
    button.innerText = language;

    button.addEventListener("click", (e) => {
      e.stopPropagation();
      closeActiveDropdown();
      goNext(language);
    });

    dropdown.appendChild(button);
  });

  parent.appendChild(dropdown);
  activeDropdown = parent;
}


// Close dropdown
function closeActiveDropdown() {
  if (activeDropdown) {
    const dropdown = activeDropdown.querySelector(".dropdown");

    if (dropdown) {
      dropdown.remove();
    }

    activeDropdown = null;
  }
}


// Click outside closes dropdown and removes active highlight
document.addEventListener("click", () => {
  closeActiveDropdown();

  document.querySelectorAll(".flag-card").forEach(item => {
    item.classList.remove("active");
  });
});


// Go to next page
function goNext(language) {
  window.location.href = `assistant.html?lang=${encodeURIComponent(language)}`;

  // Later:
  // window.location.href = `assistant.html?lang=${encodeURIComponent(language)}`;
}