let room;

function goBack() {
  window.location.href = "flags.html";
}

function getSelectedLanguage() {
  const params = new URLSearchParams(window.location.search);
  return params.get("lang") || "English";
}

function languageNameToCode(language) {
  const map = {
    Arabic: "ar",
    English: "en",
    Hindi: "hi",
    Malayalam: "ml",
    Tamil: "ta",
    Urdu: "ur",
    Pashto: "ps",
    Russian: "ru",
    Chinese: "zh",
    Indonesian: "id",
    Bengali: "bn",
    Amharic: "am",
    Tagalog: "tl",
    Zulu: "zu",
    Nepali: "ne",
    Turkish: "tr",
    Spanish: "es",
    German: "de",
    French: "fr",
    Japanese: "ja",
    Korean: "ko",
    Sinhala: "si",
    Thai: "th",
    Swahili: "sw",
    Afrikaans: "af",
    Uzbek: "uz",
    Somali: "so",
    Portuguese: "pt"
  };

  return map[language] || "en";
}


function languageToRegion(lang) {
  const map = {
    ar: "middle_east",
    en: "usa",

    hi: "south_asia",
    ur: "south_asia",
    ml: "south_asia",
    ta: "south_asia",
    bn: "south_asia",
    ne: "south_asia",
    si: "south_asia",
    ps: "south_asia",

    tl: "east_asia",
    id: "east_asia",
    th: "east_asia",
    zh: "east_asia",
    ja: "east_asia",
    ko: "east_asia",

    sw: "africa",
    am: "africa",
    so: "africa",
    zu: "africa",
    af: "africa",

    fr: "europe",
    de: "europe",
    es: "europe",
    ru: "europe",
    pt: "europe",
    tr: "europe",
    uz: "europe"
  };

  return map[lang] || "usa";
}


async function startSession() {
  if (room) {
    console.log("Session already running");
    return;
  }
  try {
    const selectedLanguage = getSelectedLanguage();
    const langCode = languageNameToCode(selectedLanguage);
    const region = languageToRegion(langCode);

    const response = await fetch(`/token?lang=${langCode}&region=${region}`);
    const data = await response.json();

    room = new LivekitClient.Room();
    const subtitleBox = document.getElementById("subtitleBox");

    room.on(LivekitClient.RoomEvent.TranscriptionReceived, (segments, participant) => {
      if (!subtitleBox) return;

      const text = segments
      .map(segment => segment.text)
      .join(" ")
      .trim();
    
    if (text) {
      subtitleBox.innerText = text; }
    
    });



    room.on(LivekitClient.RoomEvent.TrackSubscribed, (track, publication, participant) => {
  console.log("Track subscribed:", track.kind, "from:", participant.identity);

  if (track.kind === "audio") {
    const audioElement = track.attach();
    audioElement.autoplay = true;
    audioElement.playsInline = true;
    audioElement.muted = false;
    audioElement.volume = 1;

    document.body.appendChild(audioElement);

    audioElement.play().catch((err) => {
      console.warn("Audio play blocked:", err);
    });
  }

  if (track.kind === "video") {
    const videoElement = document.getElementById("avatarVideo");

    track.attach(videoElement);

    videoElement.autoplay = true;
    videoElement.playsInline = true;
    videoElement.muted = true; // video muted is okay; audio comes separately

    videoElement.play().catch((err) => {
      console.warn("Video play blocked:", err);
    });
  }
});

    // room.on(LivekitClient.RoomEvent.TrackSubscribed, (track) => {
    //   if (track.kind === "audio") {
    //     const audioElement = track.attach();
    //     document.body.appendChild(audioElement);
    //   }

    //   if (track.kind === "video") {
    //     const videoElement = document.getElementById("avatarVideo");
    //     track.attach(videoElement);
    //   }
    // });

    console.log("Joining with:", { langCode, region });
    console.log("Token response:", data);
    
    await room.connect(data.wsUrl, data.token);

    await room.localParticipant.setMicrophoneEnabled(true);

    console.log("Connected to LiveKit room:", data.room);
    console.log("Selected language:", selectedLanguage, langCode);

  } catch (error) {
    console.error("LiveKit connection failed:", error);
    alert("Could not connect to Hala. Please check if LiveKit, token server, and agent are running.");
  }
}

async function endSession() {
  if (room) {
    room.disconnect();
    room = null;
  }

  window.location.href = "flags.html";
}

document.addEventListener("DOMContentLoaded", () => {
  const micButton = document.querySelector(".mic-button");
  const endButton = document.querySelector(".end-button");

  micButton.addEventListener("click", startSession);
  endButton.addEventListener("click", endSession);
});
